"""
Synthesis Agent — Resolves conflicts, builds unified narrative.
Creates timeline, pain clusters, and decision maker profile.
"""
import logging
from app.services.llm_client import chat_completion_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the SYNTHESIS_AGENT for DataVex, a sales intelligence platform.

You receive all previous agent outputs (financial, tech, conflict analysis) and build a unified intelligence narrative.

Produce a JSON object with:
{
  "descriptor": "Enterprise SaaS · 2,400 employees · Series D · $180M ARR",
  "receptivity": "HIGH — ACT WITHIN 90 DAYS",
  "pain_tags": ["HIGH PAIN", "HIGH PAIN", "MED PAIN"],
  "timeline": [
    {"date": "2025.11", "type": "positive", "label": "CEO keynote at SaaStr Annual: Enterprise-first by end of 2026.", "source": "SAASTR ANNUAL"},
    {"date": "2025.10", "type": "pressure", "label": "Q3 earnings miss — revenue $42.1M vs $44.8M consensus.", "source": "SEC FILING"}
  ],
  "decision_maker": {
    "name": "Marcus Rivera",
    "role": "VP Engineering · Reports to interim CTO",
    "topics": ["Platform Migration", "Developer Velocity", "Cost-per-Deploy"],
    "messaging": {
      "angle": "Your infra migration is exposed — pipeline issues will bottleneck the enterprise pivot.",
      "vocab": ["deployment velocity", "platform consolidation", "eng leverage"],
      "tone": "Direct"
    }
  },
  "outreach": {
    "email": "A full email draft addressing the decision maker directly with specific evidence...",
    "linkedin": "A shorter LinkedIn message...",
    "opener": "A cold call opener question...",
    "footnote": "GENERATED FROM: Q3 margin signal + CTO departure + Kubernetes roles"
  },
  "capability_match": [
    {"pain": "Connector failures causing 4hr delays", "source": "GITHUB ISSUES", "severity": "HIGH", "capability": "Real-Time Pipeline Repair"},
    {"pain": "Monolithic warehouse costs exploding", "source": "INVESTOR REPORT", "severity": "HIGH", "capability": "Legacy Stack Migration"}
  ],
  "strongest_match": {
    "score": 75,
    "capability": "Real-Time Pipeline Repair",
    "pain": "Connector failures causing 4hr delays",
    "gap": "Vector Search (no detected need)"
  },
  "market_timing_score": 18,
  "market_timing_max": 20,
  "leadership_score": 15,
  "leadership_max": 20
}

DataVex capabilities to match against:
1. Real-Time Pipeline Repair (score 96)
2. Legacy Stack Migration (score 84)
3. Schema Evolution Management (score 88)
4. Data Observability Layer (score 91)
5. Vector Search Infrastructure (score 73)

Timeline should have 4-6 entries. Outreach must be specific and evidence-based.
The decision maker should be a real person if found, otherwise infer the most likely target persona.
Map company pains to DataVex capabilities.

Return ONLY valid JSON."""


async def run(
    finance_data: dict,
    tech_data: dict,
    conflict_data: dict,
    raw_data: dict,
    company_name: str,
) -> dict:
    """
    Build unified intelligence narrative from all agent outputs.
    """
    logger.info(f"SYNTHESIS_AGENT: building narrative for '{company_name}'")

    import json

    context = f"""Company: {company_name}

FINANCIAL ANALYSIS:
{json.dumps(finance_data, indent=2, default=str)[:3000]}

TECH ANALYSIS:
{json.dumps(tech_data, indent=2, default=str)[:3000]}

CONFLICT ANALYSIS:
{json.dumps(conflict_data, indent=2, default=str)[:2000]}

RAW WEB RESULTS (key snippets):
"""

    for wr in raw_data.get("web_results", [])[:10]:
        context += f"- {wr.get('title', '')}: {wr.get('body', '')}\n"

    for nr in raw_data.get("news_results", [])[:5]:
        context += f"- [NEWS] {nr.get('title', '')}: {nr.get('body', '')}\n"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]

    result = await chat_completion_json(messages, temperature=0.5, max_tokens=6000)

    # Ensure required fields
    defaults = {
        "descriptor": "",
        "receptivity": "MEDIUM — MONITOR",
        "pain_tags": [],
        "timeline": [],
        "decision_maker": {},
        "outreach": {},
        "capability_match": [],
        "strongest_match": {},
    }
    for key, val in defaults.items():
        if key not in result:
            result[key] = val

    logger.info(f"SYNTHESIS_AGENT: built narrative with {len(result.get('timeline', []))} timeline events, {len(result.get('capability_match', []))} capability matches")
    return result
