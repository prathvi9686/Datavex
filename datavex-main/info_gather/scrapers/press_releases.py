"""
Press Release Scraper
Sources:
  1. Company website News/Blog RSS feed
  2. Company News page HTML crawl
  3. PR Newswire / Business Wire (public search)
  4. Google News RSS
"""
import re
import feedparser
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from loguru import logger
from utils.http import safe_get, get_session

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# Pivot signal keywords in press releases
PIVOT_TERMS = [
    "pivot", "strategic shift", "expanding into", "moving from", "new direction",
    "restructur", "realign", "transform", "launch", "new platform", "AI-first",
    "leadership", "acqui", "partner", "rebrand", "new product", "new service",
]


def scrape_press_releases(
    company_name: str,
    domain: str,
    news_page_url: str | None = None,
    limit: int = 20
) -> list[dict]:
    """
    Aggregate press releases from multiple sources.
    Returns list of dicts with {title, content, published_date, source_url}.
    """
    results = []

    # 1. Try RSS feed first (fastest)
    rss_results = _try_rss_feeds(domain, company_name)
    results.extend(rss_results)

    # 2. Try company news page
    if news_page_url and len(results) < limit:
        html_results = _scrape_news_page(news_page_url, company_name)
        results.extend(html_results)

    # 3. Google News RSS as fallback
    if len(results) < 5:
        gn_results = _scrape_google_news(company_name)
        results.extend(gn_results)

    # Deduplicate by URL
    seen, unique = set(), []
    for r in results:
        if r["source_url"] not in seen:
            seen.add(r["source_url"])
            unique.append(r)

    # Tag each release with detected signals
    for pr in unique:
        pr["pivot_signals"] = _detect_pivot_signals(pr["title"] + " " + pr.get("content", ""))

    logger.info(f"[{company_name}] Press releases: {len(unique)} collected")
    return unique[:limit]


def _try_rss_feeds(domain: str, company_name: str) -> list[dict]:
    """Try common RSS feed paths on the company domain."""
    results = []
    session = get_session()
    base = domain if domain.startswith("http") else f"https://{domain}"

    rss_paths = [
        "/feed", "/rss", "/news/feed", "/blog/feed",
        "/press/rss", "/newsroom/feed", "/news.rss",
        "/atom.xml", "/feed.xml", "/rss.xml",
    ]

    for path in rss_paths:
        url = base + path
        try:
            resp = safe_get(url, session, timeout=8)
            if "xml" in resp.headers.get("content-type", "") or resp.text.strip().startswith("<?xml"):
                feed = feedparser.parse(resp.text)
                for entry in feed.entries[:15]:
                    results.append({
                        "company_name":   company_name,
                        "title":          entry.get("title", ""),
                        "content":        entry.get("summary", "")[:3000],
                        "published_date": entry.get("published", ""),
                        "source_url":     entry.get("link", url),
                    })
                if results:
                    logger.info(f"[{company_name}] RSS found at {url}")
                    break
        except Exception:
            continue

    return results


def _scrape_news_page(news_url: str, company_name: str) -> list[dict]:
    """Crawl a company's news/press page and extract article links."""
    results = []
    session = get_session()
    try:
        resp = safe_get(news_url, session)
        soup = BeautifulSoup(resp.text, "lxml")

        article_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            full_url = urljoin(news_url, href)
            if _looks_like_article(text, href) and full_url not in article_links:
                article_links.append((text, full_url))

        for title, article_url in article_links[:15]:
            article = _fetch_article(title, article_url, company_name, session)
            if article:
                results.append(article)

    except Exception as e:
        logger.debug(f"News page scrape failed ({news_url}): {e}")

    return results


def _fetch_article(title: str, url: str, company_name: str, session) -> dict | None:
    try:
        resp = safe_get(url, session)
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup.select("nav, footer, header, script, style, aside"):
            tag.decompose()
        content = soup.get_text(separator=" ", strip=True)[:4000]
        date = _extract_date(content)
        return {
            "company_name":   company_name,
            "title":          title[:500],
            "content":        content,
            "published_date": date,
            "source_url":     url,
        }
    except Exception:
        return None


def _scrape_google_news(company_name: str) -> list[dict]:
    """Get recent news via Google News RSS."""
    results = []
    queries = [
        f"{company_name} announcement",
        f"{company_name} launch",
        f"{company_name} strategy",
    ]
    for q in queries:
        url = GOOGLE_NEWS_RSS.format(query=q.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                results.append({
                    "company_name":   company_name,
                    "title":          entry.get("title", ""),
                    "content":        entry.get("summary", "")[:2000],
                    "published_date": entry.get("published", ""),
                    "source_url":     entry.get("link", ""),
                })
        except Exception as e:
            logger.debug(f"Google News RSS failed: {e}")
    return results


def _detect_pivot_signals(text: str) -> list[str]:
    text_lower = text.lower()
    return [term for term in PIVOT_TERMS if term.lower() in text_lower]


def _looks_like_article(text: str, href: str) -> bool:
    return bool(
        len(text) > 10 and
        re.search(r"(news|press|blog|article|announcement|release|post)", href, re.I)
    )


def _extract_date(text: str) -> str:
    match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*.{0,5}20\d{2}", text)
    return match.group(0) if match else ""
