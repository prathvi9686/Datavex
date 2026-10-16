"""
DataVex Backend — Web Scraper Service
General-purpose async web scraper and search engine.
"""
import httpx
import logging
import re
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(30.0, connect=10.0)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def scrape_url(url: str, max_chars: int = 8000) -> str:
    """
    Fetch a URL and extract clean text content.
    Returns cleaned text, truncated to max_chars.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Collapse whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        return text[:max_chars]

    except Exception as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return f"[Scrape failed for {url}: {str(e)}]"


def search_web(query: str, max_results: int = 8) -> list[dict]:
    """
    Search the web via DuckDuckGo and return results.
    Each result has: title, href, body.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        logger.info(f"Search '{query}': {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"Search failed for '{query}': {e}")
        return []


def search_news(query: str, max_results: int = 5) -> list[dict]:
    """
    Search recent news via DuckDuckGo News.
    Each result has: title, url, body, date, source.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
        logger.info(f"News search '{query}': {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"News search failed for '{query}': {e}")
        return []


async def scrape_multiple(urls: list[str], max_chars_per: int = 5000) -> dict[str, str]:
    """
    Scrape multiple URLs concurrently.
    Returns {url: text_content}.
    """
    import asyncio
    
    async def _scrape_one(url: str) -> tuple[str, str]:
        text = await scrape_url(url, max_chars=max_chars_per)
        return url, text

    tasks = [_scrape_one(u) for u in urls[:10]]  # cap at 10 URLs
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = {}
    for r in results:
        if isinstance(r, tuple):
            output[r[0]] = r[1]
        else:
            logger.warning(f"Scrape error: {r}")

    return output
