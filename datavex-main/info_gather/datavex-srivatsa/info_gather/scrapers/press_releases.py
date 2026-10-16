"""
Press Release Scraper — strict relevance filtering.
Only keeps articles that are genuinely ABOUT the target company's product.
"""
import re
import feedparser
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from loguru import logger
from utils.http import safe_get, get_session

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

PIVOT_TERMS = [
    "pivot", "strategic shift", "expanding into", "moving from", "new direction",
    "restructur", "realign", "transform", "launch", "new platform", "AI-first",
    "leadership", "acqui", "partner", "rebrand", "new product", "agentic",
    "agent", "rebuild", "reinvent", "announce", "release",
]

# Title patterns that are clearly not about the company's product
NOISE_PATTERNS = [
    r"notion capital",
    r"notion systems",
    r"notion\.online",
    r"notion new music",
    r"notion festival",
    r"notion award",
    r"notion magazine",
    r"osiris.*notion",
]


def scrape_press_releases(
    company_name: str,
    domain: str,
    news_page_url: str | None = None,
    limit: int = 20,
) -> list[dict]:
    results = []

    results.extend(_try_rss_feeds(domain, company_name))

    if news_page_url and len(results) < limit:
        results.extend(_scrape_news_page(news_page_url, company_name))

    if len(results) < 5:
        results.extend(_scrape_google_news(company_name, domain))

    # Deduplicate, clean, filter
    seen, unique = set(), []
    for r in results:
        url   = r.get("source_url", "")
        title = r.get("title", "")

        if url in seen:
            continue
        if _is_noise(title):
            logger.debug(f"Filtered noise: {title[:80]}")
            continue
        # Must be genuinely about this company — title must mention company name
        # OR come from the company's own RSS (those are always relevant)
        if r.get("_source") != "rss" and company_name.lower() not in title.lower():
            logger.debug(f"Filtered unrelated: {title[:80]}")
            continue

        seen.add(url)

        r["content"]       = _strip_html(r.get("content", ""))[:3000]
        r["pivot_signals"] = _detect_pivot_signals(title + " " + r["content"])
        r.pop("_source", None)
        unique.append(r)

    logger.info(f"[{company_name}] Press releases: {len(unique)} collected (filtered)")
    return unique[:limit]


def _try_rss_feeds(domain: str, company_name: str) -> list[dict]:
    results = []
    session = get_session()
    base = domain if domain.startswith("http") else f"https://{domain}"
    rss_paths = [
        "/feed", "/rss", "/news/feed", "/blog/feed", "/press/rss",
        "/newsroom/feed", "/news.rss", "/atom.xml", "/feed.xml", "/rss.xml",
    ]
    for path in rss_paths:
        url = base + path
        try:
            resp = safe_get(url, session, timeout=8)
            ct = resp.headers.get("content-type", "")
            if "xml" in ct or resp.text.strip().startswith("<?xml"):
                feed = feedparser.parse(resp.text)
                for entry in feed.entries[:15]:
                    results.append({
                        "company_name":   company_name,
                        "title":          entry.get("title", ""),
                        "content":        _strip_html(entry.get("summary", "")),
                        "published_date": entry.get("published", ""),
                        "source_url":     entry.get("link", url),
                        "_source":        "rss",
                    })
                if results:
                    logger.info(f"[{company_name}] RSS at {url}")
                    break
        except Exception:
            continue
    return results


def _scrape_news_page(news_url: str, company_name: str) -> list[dict]:
    results = []
    session = get_session()
    try:
        resp = safe_get(news_url, session)
        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            full = urljoin(news_url, a["href"])
            if _looks_like_article(text, a["href"]) and full not in seen:
                seen.add(full)
                article = _fetch_article(text, full, company_name, session)
                if article:
                    results.append(article)
            if len(results) >= 15:
                break
    except Exception as e:
        logger.debug(f"News page scrape failed ({news_url}): {e}")
    return results


def _fetch_article(title: str, url: str, company_name: str, session) -> dict | None:
    try:
        resp = safe_get(url, session)
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup.select("nav,footer,header,script,style,aside"):
            tag.decompose()
        content = soup.get_text(" ", strip=True)[:3000]
        return {
            "company_name":   company_name,
            "title":          title[:500],
            "content":        content,
            "published_date": _extract_date(content),
            "source_url":     url,
            "_source":        "news_page",
        }
    except Exception:
        return None


def _scrape_google_news(company_name: str, domain: str) -> list[dict]:
    """
    Targeted queries that require the company name to be in the result.
    All results are post-filtered to drop non-company articles.
    """
    results = []
    queries = [
        f'"{company_name}" product launch OR announcement',
        f'"{company_name}" AI agents OR agentic',
        f'"{company_name}" revenue strategy',
        f'"{company_name}" new feature release',
    ]
    for q in queries:
        url = GOOGLE_NEWS_RSS.format(query=q.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                title   = entry.get("title", "")
                content = _strip_html(entry.get("summary", "")) or title
                results.append({
                    "company_name":   company_name,
                    "title":          title,
                    "content":        content,
                    "published_date": entry.get("published", ""),
                    "source_url":     entry.get("link", ""),
                    "_source":        "google_news",
                })
        except Exception as e:
            logger.debug(f"Google News failed: {e}")
    return results


def _is_noise(title: str) -> bool:
    t = title.lower()
    return any(re.search(p, t) for p in NOISE_PATTERNS)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "lxml").get_text(" ", strip=True)


def _detect_pivot_signals(text: str) -> list[str]:
    t = text.lower()
    return [term for term in PIVOT_TERMS if term.lower() in t]


def _looks_like_article(text: str, href: str) -> bool:
    return bool(
        len(text) > 10 and
        re.search(r"(news|press|blog|article|announcement|release|post)", href, re.I)
    )


def _extract_date(text: str) -> str:
    m = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*.{0,5}20\d{2}",
        text
    )
    return m.group(0) if m else ""
