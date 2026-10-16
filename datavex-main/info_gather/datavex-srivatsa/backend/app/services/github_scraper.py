"""
DataVex Backend — GitHub Scraper Service
Fetches data from GitHub REST API for tech signal analysis.
"""
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def search_repos(query: str, max_results: int = 5) -> list[dict]:
    """
    Search GitHub repos by org/company name.
    Returns list of {name, full_name, description, stars, language, open_issues, url}.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{GITHUB_API}/search/repositories",
                params={"q": query, "sort": "stars", "per_page": max_results},
                headers=HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        repos = []
        for item in data.get("items", [])[:max_results]:
            repos.append({
                "name": item.get("name", ""),
                "full_name": item.get("full_name", ""),
                "description": item.get("description", ""),
                "stars": item.get("stargazers_count", 0),
                "language": item.get("language", ""),
                "open_issues": item.get("open_issues_count", 0),
                "url": item.get("html_url", ""),
                "updated_at": item.get("updated_at", ""),
            })

        logger.info(f"GitHub repo search '{query}': {len(repos)} results")
        return repos

    except Exception as e:
        logger.warning(f"GitHub repo search failed for '{query}': {e}")
        return []


async def search_issues(query: str, max_results: int = 10) -> list[dict]:
    """
    Search GitHub issues by company/tech keywords.
    Returns list of {title, body_preview, state, labels, repo, url, created_at}.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{GITHUB_API}/search/issues",
                params={"q": query, "sort": "created", "order": "desc", "per_page": max_results},
                headers=HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        issues = []
        for item in data.get("items", [])[:max_results]:
            body = item.get("body", "") or ""
            issues.append({
                "title": item.get("title", ""),
                "body_preview": body[:300],
                "state": item.get("state", ""),
                "labels": [l.get("name", "") for l in item.get("labels", [])],
                "repo": item.get("repository_url", "").split("/")[-1] if item.get("repository_url") else "",
                "url": item.get("html_url", ""),
                "created_at": item.get("created_at", ""),
            })

        logger.info(f"GitHub issues search '{query}': {len(issues)} results")
        return issues

    except Exception as e:
        logger.warning(f"GitHub issues search failed for '{query}': {e}")
        return []


async def get_org_repos(org: str, max_results: int = 10) -> list[dict]:
    """
    Get repositories for a GitHub organization.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{GITHUB_API}/orgs/{org}/repos",
                params={"sort": "updated", "per_page": max_results},
                headers=HEADERS,
            )
            resp.raise_for_status()
            items = resp.json()

        repos = []
        for item in items[:max_results]:
            repos.append({
                "name": item.get("name", ""),
                "full_name": item.get("full_name", ""),
                "description": item.get("description", ""),
                "stars": item.get("stargazers_count", 0),
                "language": item.get("language", ""),
                "open_issues": item.get("open_issues_count", 0),
                "url": item.get("html_url", ""),
            })

        return repos

    except Exception as e:
        logger.warning(f"GitHub org repos failed for '{org}': {e}")
        return []
