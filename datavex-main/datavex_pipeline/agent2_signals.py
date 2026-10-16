import logging
import json

logger = logging.getLogger("datavex_pipeline.agent2")


# ---------------------------------------------------
# SIGNAL CLASSIFICATION
# ---------------------------------------------------

EXPANSION_TYPES = {"HIRING", "FUNDING", "PRODUCT", "GTM"}
STRAIN_TYPES = {"INFRA"}
RISK_TYPES = {"NEGATIVE"}


# ---------------------------------------------------
# KEYWORD PATTERNS
# ---------------------------------------------------

SIGNAL_PATTERNS = {
    "HIRING": ["hiring", "open roles", "expanding team"],
    "FUNDING": ["series a", "series b", "series c", "raised", "valuation"],
    "INFRA": ["latency", "performance", "pipeline", "workloads", "kubernetes", "spark"],
    "PRODUCT": ["launch", "release", "new feature"],
    "GTM": ["enterprise customers", "partnership", "reseller", "strategic alliance"],
}

NEGATIVE_PATTERNS = [
    "layoff", "downsizing", "cost cutting", "budget cuts",
    "reducing spend", "churn", "outage", "incident",
    "downtime", "migration away", "shutdown"
]


# ---------------------------------------------------
# WEIGHTS
# ---------------------------------------------------

EXPANSION_WEIGHT = 0.4
STRAIN_WEIGHT = 0.6
RISK_WEIGHT = 0.5


# ---------------------------------------------------
# RECENCY
# ---------------------------------------------------

def recency_weight(days):
    if days is None:
        return 0.5
    if days <= 7:
        return 1.0
    elif days <= 30:
        return 0.8
    elif days <= 90:
        return 0.5
    else:
        return 0.3


# ---------------------------------------------------
# STRENGTH
# ---------------------------------------------------

def strength_multiplier(text):
    text = text.lower()

    if "billion" in text:
        return 1.3
    if "series c" in text or "series d" in text:
        return 1.2
    if "enterprise customers" in text:
        return 1.2
    if "series b" in text:
        return 1.1

    return 1.0


# ---------------------------------------------------
# FIT TYPE CLASSIFICATION
# ---------------------------------------------------
# Companies matching these names are consulting/SI competitors, not sales
# targets. Agent 3 skips anything classified as COMPETITOR.
KNOWN_COMPETITORS = {
    "accenture", "deloitte", "infosys", "tcs", "tata consultancy",
    "wipro", "cognizant", "capgemini", "mckinsey", "ibm consulting",
}


def classify_fit_type(company_name: str) -> str:
    name = (company_name or "").lower()
    if any(comp in name for comp in KNOWN_COMPETITORS):
        return "COMPETITOR"
    return "TARGET"


# ---------------------------------------------------
# LOAD CACHE
# ---------------------------------------------------

def load_cache():
    try:
        with open("search_cache.json") as f:
            return json.load(f)
    except:
        return {}


# ---------------------------------------------------
# COLLECT EVIDENCE
# ---------------------------------------------------

def collect_evidence(cache, company):
    block = cache.get(company, {})
    signals_block = block.get("signals", {})

    items = []

    for cat, entries in signals_block.items():
        for e in entries:
            items.append({
                "text": e.get("text", ""),
                "recency_days": e.get("recency_days"),
                "source": e.get("source", cat)
            })

    return items


# ---------------------------------------------------
# EXTRACT SIGNALS
# ---------------------------------------------------

def extract_signals(evidence):
    raw = []

    for item in evidence:
        text = item["text"].lower()

        # negative
        for kw in NEGATIVE_PATTERNS:
            if kw in text:
                raw.append({
                    "type": "NEGATIVE",
                    "recency_days": item["recency_days"],
                    "text": item["text"]
                })
                break

        # positive
        for t, kws in SIGNAL_PATTERNS.items():
            for kw in kws:
                if kw in text:
                    raw.append({
                        "type": t,
                        "recency_days": item["recency_days"],
                        "text": item["text"]
                    })
                    break

    return raw


# ---------------------------------------------------
# DEDUP
# ---------------------------------------------------

def dedup(signals):
    best = {}

    for s in signals:
        t = s["type"]
        r = s.get("recency_days") or 999

        if t not in best or r < (best[t].get("recency_days") or 999):
            best[t] = s

    return list(best.values())


# ---------------------------------------------------
# COMPUTE COMPONENT SCORES
# ---------------------------------------------------

def compute_scores(signals):

    expansion = 0.0
    strain = 0.0
    risk = 0.0

    for s in signals:
        rec = recency_weight(s.get("recency_days"))
        strength = strength_multiplier(s.get("text", ""))

        val = rec * strength

        if s["type"] in EXPANSION_TYPES:
            expansion += val
        elif s["type"] in STRAIN_TYPES:
            strain += val
        elif s["type"] in RISK_TYPES:
            risk += val

    expansion = min(expansion, 1.0)
    strain = min(strain, 1.0)
    risk = min(risk, 1.0)

    return expansion, strain, risk


# ---------------------------------------------------
# FINAL PAIN SCORE
# ---------------------------------------------------

def compute_pain(expansion, strain, risk):

    pain = (
        STRAIN_WEIGHT * strain +
        EXPANSION_WEIGHT * expansion -
        RISK_WEIGHT * risk
    )

    return round(max(0.0, min(pain, 1.0)), 3)


# ---------------------------------------------------
# LLM SIGNAL CONFIDENCE (additive post-processing)
# ---------------------------------------------------

def _validate_signal_confidence(company_name: str, industry: str, signals: list) -> list:
    """
    Call Ollama to rate each signal's credibility for this company.
    Returns signals with 'llm_confidence' added: VERIFIED | PLAUSIBLE | UNVERIFIED
    Falls back gracefully — marks all UNVERIFIED if Ollama unavailable.
    Rules always ran first; this is purely additive.
    """
    try:
        from ollama_client import ollama_call, ollama_available
    except ImportError:
        for s in signals:
            s["llm_confidence"] = "UNVERIFIED"
        return signals

    if not signals:
        return signals

    # Batch all signals in one call to avoid N requests per company
    signal_list = "\n".join(
        f"{i+1}. [{s['type']}] {s.get('text', '')[:120]}"
        for i, s in enumerate(signals)
    )

    prompt = (
        f"Company: {company_name}\n"
        f"Industry: {industry}\n\n"
        f"The following signals were detected about this company:\n{signal_list}\n\n"
        "For each signal, rate its credibility as exactly one of: VERIFIED, PLAUSIBLE, or UNVERIFIED.\n"
        "VERIFIED = directly confirms a real event. PLAUSIBLE = consistent but indirect. UNVERIFIED = uncertain.\n"
        "Reply with ONLY a JSON array in this exact format:\n"
        '[{"index": 1, "confidence": "VERIFIED"}, {"index": 2, "confidence": "PLAUSIBLE"}, ...]'
    )

    result = ollama_call(prompt, model="llama3.1", timeout=25, expect_json=False)

    # Parse numbered confidence array from response
    confidence_map = {}
    if result:
        try:
            import re, json as _json
            # Try to find JSON array
            arr_match = re.search(r"\[[\s\S]+?\]", result)
            if arr_match:
                parsed = _json.loads(arr_match.group(0))
                for item in parsed:
                    idx = int(item.get("index", 0)) - 1
                    conf = item.get("confidence", "UNVERIFIED").upper()
                    if conf in {"VERIFIED", "PLAUSIBLE", "UNVERIFIED"}:
                        confidence_map[idx] = conf
        except Exception:
            pass

    for i, s in enumerate(signals):
        s["llm_confidence"] = confidence_map.get(i, "UNVERIFIED")

    return signals


# ---------------------------------------------------
# MAIN RUN
# ---------------------------------------------------

def run(candidates):
    cache = load_cache()
    results = []

    for c in candidates:
        evidence = collect_evidence(cache, c.company_name)
        raw = extract_signals(evidence)
        signals = dedup(raw)

        expansion, strain, risk = compute_scores(signals)
        pain = compute_pain(expansion, strain, risk)

        if pain > 0.7:
            level = "HIGH"
        elif pain > 0.35:
            level = "MEDIUM"
        else:
            level = "LOW"

        # ── LLM: validate each signal's credibility (additive) ──
        industry = cache.get(c.company_name, {}).get("meta", {}).get("industry", "")
        signals = _validate_signal_confidence(c.company_name, industry, signals)

        results.append({
            "company_name":   c.company_name,
            "fit_type":       classify_fit_type(c.company_name),
            "company_state":  "SCALE_UP",

            "expansion_score": round(expansion, 3),
            "strain_score":    round(strain, 3),
            "risk_score":      round(risk, 3),

            "pain_score":  pain,
            "pain_level":  level,

            # signals now include 'llm_confidence' per item (additive only)
            "signals": signals,
        })

    return results