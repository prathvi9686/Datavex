"""
Tech Agent — Analyzes technical signals from scraped data.
Detects tech stack, hiring patterns, GitHub issues, engineering culture.
"""
import json
import logging
from app.services.llm_client import chat_completion_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the TECH_AGENT for DataVex, a sales intelligence platform.

You analyze raw scraped data about a company and extract technical / engineering signals.

Given the raw data, produce a JSON object with:
{
  "hiring": [
    {"category": "Engineering", "count": 24, "type": "positive"},
    {"category": "DevOps / SRE", "count": 9, "type": "positive"},
    {"category": "Leadership", "count": 3, "type": "warning"},
    {"category": "Sales", "count": 5, "type": "neutral"}
  ],
  "tech_signals": [
    {"signal": "9 Kubernetes migration roles — infra overhaul confirmed", "type": "positive", "source": "JOB BOARDS"},
    {"signal": "22 legacy pipeline issues on GitHub — 14 P0", "type": "pressure", "source": "GITHUB ISSUES"}
  ],
  "pain_clusters": [
    {
      "title": "Data Pipeline Failures",
      "evidence": [
        {"source": "GH", "text": "22 issues tagged legacy-pipeline — 14 marked P0"},
        {"source": "G2", "text": "Data sync breaks every time we scale past 10K events/sec"},
        {"source": "JD", "text": "Senior Data Engineer role: Rebuild batch processing layer"}
      ]
    },
    {
      "title": "Deployment Velocity",
      "evidence": [
        {"source": "GH", "text": "CI/CD pipeline average build time: 34 minutes"},
        {"source": "JD", "text": "DevOps Lead: Reduce deployment cycle from weekly to daily"}
      ]
    }
  ],
  "tech_stack_detected": ["Kubernetes", "Python", "PostgreSQL"],
  "tech_health_score": 28,
  "tech_health_max": 35
}

Create 2-4 pain clusters based on evidence found. Each should have 2-3 evidence items.
Use realistic data based on what you find. Be specific with numbers and quotes.

Return ONLY valid JSON."""


async def run(raw_data: dict) -> dict:
    """
    Analyze tech/engineering signals from scraped data.
    """
    company = raw_data.get("company_name", "Unknown")
    logger.info(f"TECH_AGENT: analyzing tech signals for '{company}'")

    # Prepare context
    context_parts = [f"Company: {company}"]

    # GitHub data
    for repo in raw_data.get("github_repos", [])[:5]:
        context_parts.append(f"[REPO] {repo.get('full_name', '')}: {repo.get('description', '')} — {repo.get('stars', 0)} stars, {repo.get('open_issues', 0)} open issues, lang: {repo.get('language', '')}")

    for issue in raw_data.get("github_issues", [])[:10]:
        labels = ", ".join(issue.get("labels", []))
        context_parts.append(f"[ISSUE] {issue.get('title', '')} [{issue.get('state', '')}] labels: {labels} — {issue.get('body_preview', '')[:200]}")

    # Job postings and tech-related web results
    for wr in raw_data.get("web_results", [])[:15]:
        title = wr.get("title", "")
        body = wr.get("body", "")
        if any(kw in title.lower() + body.lower() for kw in [
            "hiring", "engineer", "developer", "devops", "sre", "tech",
            "stack", "kubernetes", "migration", "infrastructure", "job",
            "role", "glassdoor", "review", "g2"
        ]):
            context_parts.append(f"[WEB] {title}: {body}")

    for url, text in list(raw_data.get("scraped_pages", {}).items())[:3]:
        context_parts.append(f"[PAGE] {url}:\n{text[:2000]}")

    context = "\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze the tech/engineering signals for this company:\n\n{context}"},
    ]

    result = await chat_completion_json(messages, temperature=0.4)

    # Ensure required structure
    if "hiring" not in result:
        result["hiring"] = []
    if "pain_clusters" not in result:
        result["pain_clusters"] = []
    if "tech_health_score" not in result:
        result["tech_health_score"] = 20
    if "tech_health_max" not in result:
        result["tech_health_max"] = 35

    logger.info(f"TECH_AGENT: detected {len(result.get('pain_clusters', []))} pain clusters, {len(result.get('hiring', []))} hiring categories")
    return result
