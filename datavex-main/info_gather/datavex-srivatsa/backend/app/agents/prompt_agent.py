"""
Prompt Agent — Converts user's natural language request into a structured scraping plan.
"""
import logging
from app.services.llm_client import chat_completion_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the PROMPT_AGENT for DataVex, a sales intelligence platform.

Your job is to take a user's natural language request and convert it into a structured scraping plan.

Given a user request like "Analyze Meridian Systems - Enterprise SaaS company", you must output a JSON object with:
- company_name: the company name to analyze
- company_slug: a URL-safe slug (lowercase, hyphens)
- industry: detected or stated industry
- keywords: list of search keywords for finding information
- github_queries: list of queries to search on GitHub
- web_queries: list of queries to search on the web (for financial, hiring, reviews, etc.)
- news_queries: list of queries to search for recent news

Be thorough — generate at least 5 web queries covering:
1. Company financials / funding / revenue
2. Company hiring / job postings
3. Company tech stack / engineering blog
4. Company reviews (G2, Glassdoor, employee reviews)
5. Company leadership / executive changes
6. Company product / market position

Return ONLY valid JSON."""


async def run(user_request: str) -> dict:
    """
    Convert a user request into a structured scraping plan.
    """
    logger.info(f"PROMPT_AGENT: processing '{user_request}'")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"User request: {user_request}"},
    ]

    result = await chat_completion_json(messages, temperature=0.3)

    # Ensure required fields
    defaults = {
        "company_name": "Unknown",
        "company_slug": "unknown",
        "industry": "Unknown",
        "keywords": [],
        "github_queries": [],
        "web_queries": [],
        "news_queries": [],
    }
    for key, val in defaults.items():
        if key not in result:
            result[key] = val

    logger.info(f"PROMPT_AGENT: plan for '{result['company_name']}' — {len(result['web_queries'])} web queries, {len(result['github_queries'])} github queries")
    return result
