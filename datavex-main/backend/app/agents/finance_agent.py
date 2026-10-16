"""
Finance Agent — Analyzes financial signals from scraped data.
Detects revenue trends, margin pressure, burn rate, funding signals.
"""
import json
import logging
from app.services.llm_client import chat_completion_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the FINANCE_AGENT for DataVex, a sales intelligence platform.

You analyze raw scraped data about a company and extract financial intelligence signals.

Given the raw data, produce a JSON object with:
{
  "financials": {
    "quarters": ["Q1 24", "Q2 24", "Q3 24", "Q4 24", "Q1 25", "Q2 25"],
    "margin": [18.2, 17.4, 16.8, 15.9, 15.1, 14.6],
    "revenue": [38.2, 40.1, 42.1, 41.3, 43.8, 44.2]
  },
  "financial_signals": [
    {"signal": "Operating margin declining 2.3% over 3 quarters", "type": "pressure", "source": "SEC FILING"},
    {"signal": "Revenue growing 15% YoY", "type": "positive", "source": "EARNINGS REPORT"}
  ],
  "funding_info": "Series D · $180M ARR",
  "burn_rate_assessment": "Moderate — spending increasing on transformation",
  "financial_health_score": 22,
  "financial_health_max": 25
}

Use realistic data based on what you find in the scraped content. If specific numbers aren't available, make reasonable estimates based on the company's industry, size, and available signals.
Quarters should cover the last 6 quarters.

Return ONLY valid JSON."""


async def run(raw_data: dict) -> dict:
    """
    Analyze financial signals from scraped data.
    """
    company = raw_data.get("company_name", "Unknown")
    logger.info(f"FINANCE_AGENT: analyzing financial signals for '{company}'")

    # Prepare context from scraped data
    context_parts = [f"Company: {company}"]

    for wr in raw_data.get("web_results", [])[:15]:
        title = wr.get("title", "")
        body = wr.get("body", "")
        if any(kw in title.lower() + body.lower() for kw in [
            "revenue", "funding", "valuation", "series", "ipo", "earnings",
            "financial", "margin", "profit", "loss", "raise", "growth"
        ]):
            context_parts.append(f"[WEB] {title}: {body}")

    for nr in raw_data.get("news_results", [])[:10]:
        title = nr.get("title", "")
        body = nr.get("body", "")
        context_parts.append(f"[NEWS] {title}: {body}")

    for url, text in list(raw_data.get("scraped_pages", {}).items())[:3]:
        context_parts.append(f"[PAGE] {url}:\n{text[:2000]}")

    context = "\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze the financial signals for this company:\n\n{context}"},
    ]

    result = await chat_completion_json(messages, temperature=0.4)

    # Ensure required structure
    if "financials" not in result:
        result["financials"] = {"quarters": [], "margin": [], "revenue": []}
    if "financial_signals" not in result:
        result["financial_signals"] = []
    if "financial_health_score" not in result:
        result["financial_health_score"] = 15
    if "financial_health_max" not in result:
        result["financial_health_max"] = 25

    logger.info(f"FINANCE_AGENT: detected {len(result.get('financial_signals', []))} signals")
    return result
