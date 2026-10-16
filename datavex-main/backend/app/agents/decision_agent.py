"""
Decision Agent — Issues final verdict, score, confidence, and recommended action window.
"""
import logging
from app.services.llm_client import chat_completion_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the DECISION_AGENT for DataVex, a sales intelligence platform.

You receive all agent analyses and the synthesis, and issue the FINAL VERDICT.

Produce a JSON object with:
{
  "verdict": "HIGH",
  "score": 87,
  "confidence": "HIGH",
  "coverage": 73,
  "window": "60–90 days",
  "recommended_persona": "VP Engineering",
  "reasoning": "Strong tech migration signals, declining margins creating urgency, receptive leadership indicated by hiring patterns.",
  "score_breakdown": [
    {"label": "Tech Signals", "value": 32, "max": 35},
    {"label": "Financial", "value": 22, "max": 25},
    {"label": "Market Timing", "value": 18, "max": 20},
    {"label": "Leadership", "value": 15, "max": 20}
  ]
}

Score rules:
- Total score is the SUM of the 4 breakdown values (max 100)
- Tech Signals (max 35): based on GitHub activity, hiring, tech stack signals
- Financial (max 25): based on revenue, margins, funding signals
- Market Timing (max 20): based on recent events, urgency indicators
- Leadership (max 20): based on executive changes, decision maker accessibility

Verdict rules:
- HIGH (score >= 75): Strong signals, act within 60-90 days
- MEDIUM (score 50-74): Monitor, act within 30-60 days
- LOW (score < 50): Long cycle, plant seeds

Confidence rules:
- HIGH: Multiple strong signal sources agree
- MEDIUM: Some signals, some gaps
- LOW: Sparse data, uncertain

Coverage (0-100): Percentage of data sources that provided useful information.

Return ONLY valid JSON."""


async def run(
    finance_data: dict,
    tech_data: dict,
    conflict_data: dict,
    synthesis_data: dict,
    company_name: str,
) -> dict:
    """
    Issue final verdict with score and confidence.
    """
    logger.info(f"DECISION_AGENT: issuing verdict for '{company_name}'")

    import json

    context = f"""Company: {company_name}

FINANCE SUMMARY:
- Health score: {finance_data.get('financial_health_score', 0)}/{finance_data.get('financial_health_max', 25)}
- Signals: {json.dumps(finance_data.get('financial_signals', []), default=str)[:1000]}

TECH SUMMARY:
- Health score: {tech_data.get('tech_health_score', 0)}/{tech_data.get('tech_health_max', 35)}
- Pain clusters: {len(tech_data.get('pain_clusters', []))}
- Hiring categories: {len(tech_data.get('hiring', []))}

CONFLICTS:
- Contradictions: {len(conflict_data.get('contradictions', []))}
- Tension level: {conflict_data.get('overall_tension', 'UNKNOWN')}
- Risks: {json.dumps(conflict_data.get('risk_factors', []), default=str)[:500]}

SYNTHESIS:
- Receptivity: {synthesis_data.get('receptivity', 'UNKNOWN')}
- Capability matches: {len(synthesis_data.get('capability_match', []))}
- Timeline events: {len(synthesis_data.get('timeline', []))}
- Market timing score: {synthesis_data.get('market_timing_score', 0)}/{synthesis_data.get('market_timing_max', 20)}
- Leadership score: {synthesis_data.get('leadership_score', 0)}/{synthesis_data.get('leadership_max', 20)}
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]

    result = await chat_completion_json(messages, temperature=0.3)

    # Ensure required fields
    if "verdict" not in result:
        result["verdict"] = "MEDIUM"
    if "score" not in result:
        result["score"] = 50
    if "confidence" not in result:
        result["confidence"] = "MEDIUM"
    if "coverage" not in result:
        result["coverage"] = 50
    if "score_breakdown" not in result:
        result["score_breakdown"] = []

    logger.info(f"DECISION_AGENT: verdict={result['verdict']}, score={result['score']}, confidence={result['confidence']}")
    return result
