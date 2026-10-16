"""
Agent 6 — "What to Sell" RAG Recommender
NEW agent. Runs AFTER Agent 4 (decisions), BEFORE Agent 5 (outreach).

How it works:
1. Build a query string from the company's profile + signals + strategy
2. Retrieve top 2-3 matching Datavex services from knowledge_base.py (ChromaDB or cosine)
3. Pass the retrieved context + company profile to llama3.1
4. LLM reasons about what to lead with and what to upsell
5. Return structured recommendation dict

Output shape:
{
    "company_name":       str,
    "lead_service":       str,
    "lead_service_reason": str,
    "upsell_services":    [str, str],
    "rag_sources_used":   [str, ...],
    "confidence":         "HIGH" | "MEDIUM" | "LOW",
}
"""
import logging
import re

logger = logging.getLogger("datavex_pipeline.agent6")


# ---------------------------------------------------
# QUERY BUILDER
# ---------------------------------------------------

def _build_query(d: dict, sig: dict | None) -> str:
    """
    Build a retrieval query string from company profile + agent4 decision.
    Used to search the ChromaDB knowledge base.
    """
    parts = []

    company = d.get("company_name", "")
    if company:
        parts.append(company)

    if sig:
        industry = sig.get("meta", {}).get("industry", "") or ""
        size     = sig.get("meta", {}).get("size", "") or ""
        state    = sig.get("company_state", "SCALE_UP")
        pain     = sig.get("pain_level", "")
        if industry: parts.append(industry)
        if size:     parts.append(f"{size} company")
        if state:    parts.append(state)
        if pain:     parts.append(f"{pain} pain")

        # Add signal types as hints
        for s in sig.get("signals", [])[:4]:
            parts.append(s.get("type", ""))

    strategy = d.get("strategy", "")
    offer    = d.get("recommended_offer", "")
    if strategy: parts.append(strategy)
    if offer:    parts.append(offer)

    intent = d.get("intent_score", 0)
    if intent > 0.7:
        parts.append("high intent")
    elif intent > 0.4:
        parts.append("medium intent")

    return " ".join(p for p in parts if p)


# ---------------------------------------------------
# LLM REASONING
# ---------------------------------------------------

def _llm_recommend(company: str, profile: dict, strategy: str, scores: dict,
                   rag_services: list) -> dict | None:
    """
    Ask Ollama: given company profile + RAG context, what should we lead with?
    Returns parsed dict or None if Ollama unavailable.
    """
    try:
        from ollama_client import ollama_call
    except ImportError:
        return None

    # Format RAG context
    rag_context = ""
    for i, svc in enumerate(rag_services, 1):
        rag_context += (
            f"\nService {i}: {svc.get('name', '')}\n"
            f"  Description: {svc.get('description', '')[:200]}\n"
            f"  Upsell: {', '.join(svc.get('upsell', []))}\n"
        )

    sig_types  = [s.get("type", "") for s in profile.get("signals", [])[:5]]
    pain_level = profile.get("pain_level", "MEDIUM")
    industry   = profile.get("meta", {}).get("industry", "") if isinstance(profile.get("meta"), dict) else ""

    prompt = (
        f"Company: {company}\n"
        f"Industry: {industry}\n"
        f"Pain level: {pain_level}\n"
        f"Strategy: {strategy}\n"
        f"Intent score: {scores.get('intent_score', 0):.0%}, "
        f"Conversion: {scores.get('conversion_score', 0):.0%}, "
        f"Deal size: {scores.get('deal_size_score', 0):.0%}\n"
        f"Observed signals: {', '.join(sig_types)}\n\n"
        f"Available Datavex services (from our capability database):\n{rag_context}\n"
        "Based on this company's profile and the services above, answer:\n"
        "1. Which service should we LEAD with? WHY is it the best fit?\n"
        "2. Which 1-2 services can we UPSELL? Why?\n"
        "3. Confidence: HIGH, MEDIUM, or LOW — how confident are you this is the right fit?\n\n"
        "Be specific. Do not invent company facts. Only use the data provided.\n"
        "Return ONLY JSON in this exact format:\n"
        '{"lead_service": "...", "lead_service_reason": "...", '
        '"upsell_services": ["...", "..."], "confidence": "HIGH"}'
    )

    result = ollama_call(
        prompt,
        system="You are a B2B solution architect matching Datavex services to company needs.",
        model="llama3.1",
        timeout=35,
        expect_json=True,
    )
    return result


# ---------------------------------------------------
# FALLBACK (rules-based when Ollama unavailable)
# ---------------------------------------------------

def _rules_recommend(strategy: str, rag_services: list) -> dict:
    """
    Simple rules-based fallback when Ollama is unavailable.
    """
    strategy_service_map = {
        "BUILD_HEAVY": "AI Infra Buildout",
        "CO_BUILD":    "ML Pipeline Audit",
        "PLATFORM":    "Data Platform Integration",
        "AUDIT":       "ML Pipeline Audit",
        "MONITOR":     "Technical Advisory Retainer",
    }

    lead_name = strategy_service_map.get(strategy, "Data Strategy Workshop")

    # Find the lead service in retrieved results
    lead = next(
        (s for s in rag_services if s.get("name") == lead_name),
        rag_services[0] if rag_services else {},
    )
    upsell_ids = lead.get("upsell", [])[:2]

    # Map IDs back to names
    id_to_name = {
        "ai_infra_buildout":        "AI Infra Buildout",
        "ml_pipeline_audit":        "ML Pipeline Audit",
        "technical_advisory":       "Technical Advisory Retainer",
        "data_strategy_workshop":   "Data Strategy Workshop",
        "data_platform_integration":"Data Platform Integration",
        "ai_readiness_assessment":  "AI Readiness Assessment",
        "real_time_streaming_build":"Real-Time Streaming Pipeline Build",
    }
    upsell_names = [id_to_name.get(u, u) for u in upsell_ids]

    return {
        "lead_service":        lead.get("name", lead_name),
        "lead_service_reason": f"Rules-based match: {strategy} strategy → {lead_name}. LLM unavailable.",
        "upsell_services":     upsell_names,
        "confidence":          "LOW",   # low confidence when LLM is unavailable
    }


# ---------------------------------------------------
# MAIN RUN
# ---------------------------------------------------

def run(decisions: list, all_signals: list | None = None) -> list[dict]:
    """
    decisions:   list of dicts from agent4
    all_signals: list of dicts from agent2 (for company profile context)

    Returns: list of recommendation dicts, one per company.
    """
    try:
        from knowledge_base import retrieve
    except ImportError:
        logger.warning("knowledge_base not available — returning minimal fallback")
        return [{"company_name": d["company_name"], "lead_service": "Technical Advisory Retainer",
                 "lead_service_reason": "KB unavailable", "upsell_services": [],
                 "rag_sources_used": [], "confidence": "LOW"} for d in decisions]

    # Build signal lookup
    sig_map = {}
    if all_signals:
        for s in all_signals:
            sig_map[s["company_name"]] = s

    results = []

    for d in decisions:
        company  = d["company_name"]
        strategy = d["strategy"]

        sig_profile = sig_map.get(company, {})

        # Step 1: RAG retrieval
        query        = _build_query(d, sig_profile)
        rag_services = retrieve(query, top_k=3)
        rag_ids      = [s.get("id", "") for s in rag_services]

        logger.info(
            "[%s] RAG query: %s → services: %s",
            company, query[:60], [s.get("name", "") for s in rag_services],
        )

        # Step 2: LLM reasoning
        llm_result = _llm_recommend(
            company=company,
            profile=sig_profile,
            strategy=strategy,
            scores={
                "intent_score":    d["intent_score"],
                "conversion_score": d["conversion_score"],
                "deal_size_score":  d["deal_size_score"],
            },
            rag_services=rag_services,
        )

        # Step 3: Build output — use LLM or fallback
        if llm_result and isinstance(llm_result, dict) and llm_result.get("lead_service"):
            output = {
                "company_name":        company,
                "lead_service":        llm_result.get("lead_service", ""),
                "lead_service_reason": llm_result.get("lead_service_reason", ""),
                "upsell_services":     llm_result.get("upsell_services", [])[:2],
                "rag_sources_used":    rag_ids,
                "confidence":          llm_result.get("confidence", "MEDIUM"),
            }
        else:
            # LLM failed — rules fallback
            fallback = _rules_recommend(strategy, rag_services)
            output   = {
                "company_name":    company,
                "rag_sources_used": rag_ids,
                **fallback,
            }

        results.append(output)
        logger.info(
            "[%s] Lead: %s | Confidence: %s",
            company, output["lead_service"], output["confidence"],
        )

    return results
