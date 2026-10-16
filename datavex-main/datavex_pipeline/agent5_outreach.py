"""
Agent 5 — Outreach Generation
Rules-first: all persona/channel/subject logic runs via hardcoded rules.
LLM layer: build_message() is replaced by Ollama generation when available.
Output shape is IDENTICAL to the original — no new keys at the top level.
Falls back to template message if Ollama is unavailable.
"""
import logging
import re

logger = logging.getLogger("datavex_pipeline.agent5")


# ---------------------------------------------------
# PERSONA SELECTION (rules — unchanged)
# ---------------------------------------------------

def decide_persona(strategy, conversion, deal_size):
    if strategy == "BUILD_HEAVY":
        return "CTO / Head of AI"
    if strategy == "CO_BUILD":
        return "VP Engineering / Director ML"
    if strategy == "PLATFORM":
        return "Head of Data Platform"
    if strategy == "AUDIT":
        return "Infra / SRE Lead"
    return "Technical Leader"


# ---------------------------------------------------
# CHANNEL SELECTION (rules — unchanged)
# ---------------------------------------------------

def decide_channel(strategy):
    if strategy in ["BUILD_HEAVY", "CO_BUILD"]:
        return "cold_email"
    if strategy == "PLATFORM":
        return "product_led_email"
    return "linkedin"


# ---------------------------------------------------
# SUBJECT LINE (rules — unchanged)
# ---------------------------------------------------

def build_subject(company, entry_point):
    return f"{company} — quick idea on {entry_point}"


# ---------------------------------------------------
# TEMPLATE MESSAGE (fallback when Ollama unavailable)
# ---------------------------------------------------

def _template_message(company, persona, entry_point, strategy, signals):
    signal_map = {
        "HIRING":  "rapid hiring and team expansion",
        "FUNDING": "recent funding and capital deployment",
        "INFRA":   "increasing infrastructure complexity",
        "PRODUCT": "new product/platform launches",
        "GTM":     "enterprise partnerships and go-to-market expansion",
    }
    readable    = [signal_map.get(s, s) for s in signals]
    signal_line = ", ".join(readable[:2]) if readable else "recent growth"

    angle_map = {
        "BUILD_HEAVY": "accelerate delivery and reduce infra burden",
        "CO_BUILD":    "augment your internal team to ship faster",
        "PLATFORM":    "optimize and extend your existing data platform",
        "AUDIT":       "identify infra bottlenecks and cost inefficiencies",
        "MONITOR":     "share insights and stay aligned as you scale",
    }
    angle = angle_map.get(strategy, "explore collaboration opportunities")

    return f"""Hi {persona},

Noticed that {company} is seeing {signal_line} — looks like the team is scaling quickly.

We typically help companies at this stage {angle}, especially around areas like {entry_point}.

Would it be useful to start with a quick 20-min conversation to explore where we can support your team?

– Datavex""".strip()


# ---------------------------------------------------
# LLM MESSAGE GENERATION
# ---------------------------------------------------

def _llm_message(company, industry, persona, entry_point, strategy, offer,
                 signals, intent, conversion, deal_size):
    """
    Replace template with Ollama-generated personalised message.
    Returns natural email string, or None if Ollama unavailable.
    Input is ONLY data already collected — LLM never invents company data.
    """
    try:
        from ollama_client import ollama_call
    except ImportError:
        return None

    signal_labels = {
        "HIRING":  "active hiring",
        "FUNDING": "recent funding",
        "INFRA":   "infrastructure signals",
        "PRODUCT": "new product launches",
        "GTM":     "enterprise partnerships",
    }
    signal_str = ", ".join(signal_labels.get(s, s) for s in signals[:3]) or "recent growth signals"

    prompt = (
        f"Company: {company}\n"
        f"Industry: {industry}\n"
        f"Target persona: {persona}\n"
        f"Sales strategy: {strategy}\n"
        f"Recommended offer: {offer}\n"
        f"Entry point: {entry_point}\n"
        f"Key signals observed: {signal_str}\n"
        f"Scores — intent: {intent:.0%}, conversion: {conversion:.0%}, deal size: {deal_size:.0%}\n\n"
        "Write a short, specific, non-generic cold outreach email for this company.\n"
        "Rules:\n"
        "- Address the persona by their role (not 'Hi there')\n"
        "- Reference the specific signals observed — don't be vague\n"
        "- One clear call to action: 20-min call\n"
        "- 3 short paragraphs max\n"
        "- Sign off as 'Datavex'\n"
        "- Do NOT use em dashes or corporate buzzwords\n"
        "Return ONLY the email body text, no subject line, no JSON."
    )

    result = ollama_call(
        prompt,
        system="You are a precision B2B outreach writer. Write naturally, not like a sales robot.",
        model="llama3.1",
        timeout=30,
    )
    if not result:
        return None

    # Strip any accidental subject line prefix
    result = re.sub(r"^subject:.*?\n", "", result, flags=re.I).strip()
    return result


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

def run(decisions, recommendations=None, all_signals=None):
    """
    decisions:       list of dicts from agent4
    recommendations: list of dicts from agent6 (optional, used for richer context)
    all_signals:     list of dicts from agent2 (optional, for industry lookup)
    Output shape IDENTICAL to original agent5 output.
    """
    outputs = []

    # Build lookup maps for optional context
    rec_map = {}
    if recommendations:
        for r in recommendations:
            rec_map[r["company_name"]] = r

    sig_map = {}
    if all_signals:
        for s in all_signals:
            sig_map[s["company_name"]] = s

    for d in decisions:
        strategy   = d["strategy"]
        conversion = d["conversion_score"]
        deal_size  = d["deal_size_score"]
        intent     = d["intent_score"]
        company    = d["company_name"]

        # Rules-based fields (unchanged)
        persona = decide_persona(strategy, conversion, deal_size)
        channel = decide_channel(strategy)
        subject = build_subject(company, d["entry_point"])

        # Get extra context if available
        rec      = rec_map.get(company, {})
        sig_data = sig_map.get(company, {})
        industry = sig_data.get("industry", "")
        offer    = rec.get("lead_service") or d.get("recommended_offer", "")
        key_sigs = d.get("key_signals", [])

        # LLM outreach (replaces template, falls back to template)
        message = _llm_message(
            company=company,
            industry=industry,
            persona=persona,
            entry_point=d["entry_point"],
            strategy=strategy,
            offer=offer,
            signals=key_sigs,
            intent=intent,
            conversion=conversion,
            deal_size=deal_size,
        )

        if not message:
            # Ollama down — use template
            message = _template_message(company, persona, d["entry_point"], strategy, key_sigs)

        # Output shape IDENTICAL to original — no new top-level keys
        outputs.append({
            "company_name":    company,
            "strategy":        strategy,
            "persona":         persona,
            "channel":         channel,
            "subject":         subject,
            "message":         message,
            "priority":        d["priority"],
            "conversion_score": conversion,
            "deal_size_score":  deal_size,
        })

    return outputs