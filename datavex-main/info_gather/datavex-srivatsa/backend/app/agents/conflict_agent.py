"""
Conflict Agent — Identifies contradictions and tensions between signals.
"""
import logging
from app.services.llm_client import chat_completion_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the CONFLICT_AGENT for DataVex, a sales intelligence platform.

You receive financial analysis and tech analysis for a company and identify CONTRADICTIONS or TENSIONS between the signals.

Contradiction examples:
- Company is hiring aggressively but margins are declining (spending vs cost pressure)
- Company claims growth but employee reviews mention layoffs
- Tech migration announced but no engineering hires to back it up
- Revenue growing but customer satisfaction declining

Produce a JSON object with:
{
  "contradictions": [
    {
      "tension": "Hiring spend rising despite cost pressure signal",
      "signal_a": "24 engineering roles posted in 60 days",
      "signal_b": "Operating margin declined 2.3% over 3 quarters",
      "interpretation": "Budget shifting from ops to transformation — confirms willingness to invest",
      "severity": "MEDIUM"
    }
  ],
  "risk_factors": [
    "CTO departure with no successor — leadership gap",
    "Customer acquisition cost rising 31%"
  ],
  "overall_tension": "HIGH"
}

Find 1-3 genuine contradictions. Be specific with sources and numbers.
Return ONLY valid JSON."""


async def run(finance_data: dict, tech_data: dict, company_name: str) -> dict:
    """
    Identify contradictions between financial and tech signals.
    """
    logger.info(f"CONFLICT_AGENT: checking contradictions for '{company_name}'")

    context = f"""Company: {company_name}

FINANCIAL ANALYSIS:
{_summarize(finance_data)}

TECH ANALYSIS:
{_summarize(tech_data)}"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]

    result = await chat_completion_json(messages, temperature=0.5)

    if "contradictions" not in result:
        result["contradictions"] = []
    if "risk_factors" not in result:
        result["risk_factors"] = []

    logger.info(f"CONFLICT_AGENT: found {len(result.get('contradictions', []))} contradictions")
    return result


def _summarize(data: dict) -> str:
    """Flatten a dict into readable text for the prompt."""
    import json
    return json.dumps(data, indent=2, default=str)[:4000]
