import logging

logger = logging.getLogger("datavex_pipeline.agent4")


# ---------------------------------------------------
# STRATEGY LOGIC
# ---------------------------------------------------

def choose_strategy(intent, conversion, deal_size):
    """
    Decide GTM motion based on scores
    """

    # High intent + good conversion → build heavy engagement
    if intent > 0.8 and conversion > 0.6:
        return "BUILD_HEAVY"

    # High intent + moderate conversion → co-build
    if intent > 0.7 and conversion > 0.4:
        return "CO_BUILD"

    # High intent but low conversion → monitor / nurture
    if intent > 0.7 and conversion <= 0.4:
        return "MONITOR"

    # Low intent → just monitor
    return "MONITOR"


# ---------------------------------------------------
# OFFER MAPPING
# ---------------------------------------------------

def map_offer(strategy):

    if strategy == "BUILD_HEAVY":
        return "custom AI infra buildout"

    if strategy == "CO_BUILD":
        return "co-development with internal team"

    if strategy == "PLATFORM":
        return "platform integration / optimization"

    if strategy == "AUDIT":
        return "infra + ML pipeline audit"

    if strategy == "MONITOR":
        return "send technical insights / case studies"

    return "general advisory support"


# ---------------------------------------------------
# ENTRY POINT MAPPING
# ---------------------------------------------------

def map_entry(strategy):

    if strategy == "BUILD_HEAVY":
        return "full architecture assessment"

    if strategy == "CO_BUILD":
        return "joint ML pipeline optimization session"

    if strategy == "PLATFORM":
        return "platform integration workshop"

    if strategy == "AUDIT":
        return "ML infra performance audit"

    if strategy == "MONITOR":
        return "send technical insights / case studies"

    return "intro discussion"


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

def run(opportunities):

    results = []

    for o in opportunities:

        intent = o["intent_score"]
        conversion = o["conversion_score"]
        deal_size = o["deal_size_score"]
        risk = o["risk_score"]

        strategy = choose_strategy(intent, conversion, deal_size)

        offer = map_offer(strategy)
        entry = map_entry(strategy)

        results.append({
            "company_name": o["company_name"],
            "priority": o["priority"],
            "strategy": strategy,
            "recommended_offer": offer,
            "entry_point": entry,

            "intent_score": intent,
            "conversion_score": conversion,
            "deal_size_score": deal_size,
            "risk_score": risk,

            # 🔥 CRITICAL FIX: pass signals forward
            "key_signals": o.get("key_signals", [])
        })

    return results