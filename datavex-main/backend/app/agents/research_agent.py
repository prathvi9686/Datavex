"""
Research Agent — Scrapes data from multiple public sources.
Collects raw data for other agents to analyze.
"""
import asyncio
import logging
from app.services.scraper import search_web, search_news, scrape_multiple
from app.services.github_scraper import search_repos, search_issues

logger = logging.getLogger(__name__)


async def run(plan: dict) -> dict:
    """
    Execute the scraping plan from Prompt Agent.
    Returns a dict of raw data organized by source.
    """
    company = plan.get("company_name", "Unknown")
    logger.info(f"RESEARCH_AGENT: scraping data for '{company}'")

    results = {
        "company_name": company,
        "github_repos": [],
        "github_issues": [],
        "web_results": [],
        "news_results": [],
        "scraped_pages": {},
    }

    # 1. GitHub searches
    github_queries = plan.get("github_queries", [f"{company}"])
    for q in github_queries[:3]:
        repos = await search_repos(q, max_results=3)
        results["github_repos"].extend(repos)

        issues = await search_issues(q, max_results=5)
        results["github_issues"].extend(issues)

    # 2. Web searches (DuckDuckGo)
    web_queries = plan.get("web_queries", [f"{company} company"])
    for q in web_queries[:8]:
        web_res = search_web(q, max_results=5)
        results["web_results"].extend(web_res)

    # 3. News searches
    news_queries = plan.get("news_queries", [f"{company} news"])
    for q in news_queries[:3]:
        news_res = search_news(q, max_results=5)
        results["news_results"].extend(news_res)

    # 4. Scrape top web result URLs for deeper content
    urls_to_scrape = []
    for wr in results["web_results"][:6]:
        href = wr.get("href") or wr.get("link", "")
        if href and "linkedin.com" not in href and "glassdoor.com" not in href:
            urls_to_scrape.append(href)

    if urls_to_scrape:
        results["scraped_pages"] = await scrape_multiple(urls_to_scrape, max_chars_per=3000)

    logger.info(
        f"RESEARCH_AGENT: collected {len(results['github_repos'])} repos, "
        f"{len(results['github_issues'])} issues, "
        f"{len(results['web_results'])} web results, "
        f"{len(results['news_results'])} news articles, "
        f"{len(results['scraped_pages'])} scraped pages"
    )
    return results
