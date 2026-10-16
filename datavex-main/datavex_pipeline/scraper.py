"""
DataVex Pipeline — Web Scraper
Real-time company intelligence via cached web search data + live DDG/Brave fallback.

Strategy:
1. PRIMARY: Read from search_cache.json (pre-scraped real data)
2. FALLBACK: DDG Lite → Brave Search (with rate-limit handling)
3. LAST RESORT: demo_data.py

The cache contains verified, real data sourced from live web searches.
To refresh: delete search_cache.json and run the pipeline (or update the cache manually).
"""
import json
import logging
import os
import time
import random
import urllib.parse

logger = logging.getLogger("datavex_pipeline.scraper")

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    logger.warning("requests or bs4 not installed — scraping disabled")

# ── Load search cache ──
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_cache.json")
SEARCH_CACHE = {}
try:
    with open(CACHE_PATH, "r") as f:
        SEARCH_CACHE = json.load(f)
    logger.info(f"  📦 Loaded search cache: {len(SEARCH_CACHE)} companies")
except FileNotFoundError:
    logger.info("  📦 No search cache found — will use live search")
except Exception as e:
    logger.warning(f"  📦 Cache load error: {e}")


USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def _search_ddg_lite(query: str, max_results: int = 8) -> list[dict]:
    """Search via DDG Lite HTML POST."""
    if not HAS_DEPS:
        return []
    try:
        session = requests.Session()
        resp = session.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": query, "kl": ""},
            headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://lite.duckduckgo.com",
                "Referer": "https://lite.duckduckgo.com/",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(f"  DDG Lite: {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select("a.result-link")
        snippets = soup.select("td.result-snippet")

        results = []
        for i, link in enumerate(links[:max_results]):
            href = link.get("href", "")
            if "uddg=" in href:
                real_url = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
            else:
                real_url = href
            title = link.get_text(strip=True)
            body = snippets[i].get_text(strip=True) if i < len(snippets) else ""
            if "duckduckgo.com" in real_url:
                continue
            results.append({"title": title, "body": body, "href": real_url})

        if results:
            logger.info(f"  🦆 DDG '{query[:45]}...' → {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"  DDG error: {e}")
        return []


def _search_brave(query: str, max_results: int = 8) -> list[dict]:
    """Search via Brave Search HTML scraping."""
    if not HAS_DEPS:
        return []
    try:
        encoded = urllib.parse.quote_plus(query)
        resp = requests.get(
            f"https://search.brave.com/search?q={encoded}",
            headers={"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html"},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(f"  Brave: {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if not text or len(text) < 10 or "brave.com" in href or not href.startswith("http"):
                continue
            if href in seen:
                continue
            seen.add(href)
            parent = a.find_parent("div")
            snippet = ""
            if parent:
                for sib in parent.find_next_siblings(limit=2):
                    t = sib.get_text(strip=True)
                    if len(t) > 30:
                        snippet = t[:300]
                        break
            results.append({"title": text[:150], "body": snippet, "href": href})
            if len(results) >= max_results:
                break

        if results:
            logger.info(f"  🔍 Brave '{query[:45]}...' → {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"  Brave error: {e}")
        return []


_engine_idx = 0


def web_search(query: str, max_results: int = 8) -> list[dict]:
    """Search using DDG Lite / Brave with alternation."""
    global _engine_idx
    engines = [_search_ddg_lite, _search_brave]
    primary = engines[_engine_idx % 2]
    fallback = engines[(_engine_idx + 1) % 2]
    _engine_idx += 1

    results = primary(query, max_results)
    if not results:
        time.sleep(2)
        results = fallback(query, max_results)
    return results


def scrape_company_signals(company_name: str, domain: str = "") -> dict:
    """
    Get company signals — uses cached data (primary) or live search (fallback).
    Returns dict with keys: careers, news, tech_stack, blog
    """
    # ── Check cache first ──
    if company_name in SEARCH_CACHE:
        cached = SEARCH_CACHE[company_name]
        if "signals" in cached:
            signals = cached["signals"]
            total = sum(len(v) for v in signals.values())
            logger.info(f"  📦 CACHE HIT: {company_name} → {total} data points (REAL DATA)")
            return signals
        logger.info(f"  📦 Cache found but no signals for {company_name}")

    # ── Live search fallback ──
    logger.info(f"  🔍 Live scraping for: {company_name}")
    signals = {"careers": [], "news": [], "tech_stack": [], "blog": []}

    all_results = web_search(
        f"{company_name} hiring funding news tech stack engineering blog",
        max_results=10,
    )
    time.sleep(5)

    career_kw = ["hiring", "careers", "jobs", "job", "engineer", "open positions", "workday", "lever.co", "greenhouse"]
    news_kw = ["funding", "raised", "acquisition", "partner", "launch", "expand", "series", "investment", "revenue"]
    tech_kw = ["tech stack", "engineering", "infrastructure", "kubernetes", "aws", "cloud", "architecture", "github"]
    blog_kw = ["blog", "product update", "announcement", "release", "new feature"]

    for r in all_results:
        combined = f"{r.get('title', '')} {r.get('body', '')} {r.get('href', '')}".lower()
        text = f"{r.get('title', '')} — {r.get('body', '')}" if r.get("body") else r.get("title", "")
        if len(text.strip()) < 20:
            continue
        entry = {"text": text[:300], "source": "", "recency_days": 30}

        if any(kw in combined for kw in career_kw):
            entry["source"] = "careers"
            signals["careers"].append(entry)
        elif any(kw in combined for kw in news_kw):
            entry["source"] = "news"
            entry["recency_days"] = 20
            signals["news"].append(entry)
        elif any(kw in combined for kw in tech_kw):
            entry["source"] = "tech_stack"
            signals["tech_stack"].append(entry)
        elif any(kw in combined for kw in blog_kw):
            entry["source"] = "blog"
            signals["blog"].append(entry)
        else:
            entry["source"] = "news"
            signals["news"].append(entry)

    total = sum(len(v) for v in signals.values())
    logger.info(f"  📊 {company_name}: {total} live data points")
    return signals


def search_decision_makers(company_name: str, target_role: str) -> list[dict]:
    """
    Find real people — uses cached data (primary) or live search (fallback).
    """
    # ── Check cache first ──
    if company_name in SEARCH_CACHE:
        cached = SEARCH_CACHE[company_name]
        if "decision_makers" in cached and cached["decision_makers"]:
            people = cached["decision_makers"]
            logger.info(f"  📦 CACHE HIT: {len(people)} decision makers for {company_name} (REAL PEOPLE)")
            # Add the raw_body field for compatibility
            for p in people:
                if "raw_body" not in p:
                    p["raw_body"] = p.get("raw_title", "")
            return people

    # ── Live search fallback ──
    logger.info(f"  🔍 Live searching for {target_role} at {company_name}")
    people = []
    results = web_search(f"{company_name} {target_role} OR CTO OR founder OR CEO LinkedIn", max_results=8)

    for r in results:
        title = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href", "")
        combined = f"{title} {body}"

        if "linkedin.com" in href.lower() or "linkedin" in combined.lower():
            name = title.split(" - ")[0].split(" | ")[0].strip()
            for suffix in [" | LinkedIn", " - LinkedIn", "LinkedIn"]:
                name = name.replace(suffix, "").strip()
            name = name.split("›")[0].strip()
            if name and 2 < len(name) < 50:
                people.append({
                    "name": name, "role": target_role,
                    "source": f"linkedin: {href}",
                    "raw_title": title[:200], "raw_body": body[:200],
                })
        elif any(kw in combined.lower() for kw in ["cto", "ceo", "founder", "vp", "head of", "chief"]):
            name = title.split(" - ")[0].split(" | ")[0].strip()
            name = name.split("›")[0].strip()
            if name and 2 < len(name) < 50:
                people.append({
                    "name": name, "role": target_role,
                    "source": f"web: {href}",
                    "raw_title": title[:200], "raw_body": body[:200],
                })

    logger.info(f"  👥 Found {len(people)} contacts for {company_name}")
    return people
