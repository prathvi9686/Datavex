import logging
from models import CandidateCompany

logger = logging.getLogger("datavex_pipeline.agent1")


# ---------------------------------------------------
# CANDIDATE UNIVERSE (demo dataset)
# ---------------------------------------------------
# Small, deterministic dataset of companies with enough metadata for the
# heuristics below to filter/rank against a user's natural-language query
# and deal profile. In a production system this would be a real company
# search/index — this keeps behaviour reproducible for the demo without
# silently ignoring the caller's input (the previous version always
# returned the same 2 hardcoded companies regardless of what was asked).

CANDIDATE_UNIVERSE = [
    {
        "company_name": "MindsDB", "domain": "AI / Data Infrastructure", "industry": "AI Infra",
        "keywords": ["ai", "ml", "database", "data infrastructure", "data engineering", "machine learning"],
        "region": "US", "size_label": "MID", "employees": 150, "internal_tech_strength": 0.4,
    },
    {
        "company_name": "Databricks", "domain": "Data Platform / AI", "industry": "Data Platform",
        "keywords": ["ai", "ml", "cloud", "data platform", "cloud modernization", "data engineering", "spark"],
        "region": "US", "size_label": "LARGE", "employees": 9000, "internal_tech_strength": 0.85,
    },
    {
        "company_name": "Fractal Analytics", "domain": "AI Analytics", "industry": "AI Analytics",
        "keywords": ["ai", "analytics", "ai saas", "data engineering", "cloud modernization"],
        "region": "India", "size_label": "LARGE", "employees": 4000, "internal_tech_strength": 0.6,
    },
    {
        "company_name": "Krea.ai", "domain": "AI Infra / Inference", "industry": "AI Infra",
        "keywords": ["ai", "inference", "kubernetes", "fintech", "ai saas", "cloud modernization"],
        "region": "India", "size_label": "MID", "employees": 150, "internal_tech_strength": 0.55,
    },
    {
        "company_name": "Slice", "domain": "Fintech", "industry": "Fintech",
        "keywords": ["fintech", "cloud modernization", "data engineering", "legacy migration"],
        "region": "India", "size_label": "MID", "employees": 600, "internal_tech_strength": 0.45,
    },
    {
        "company_name": "Sarvam AI", "domain": "Sovereign AI", "industry": "AI Infra",
        "keywords": ["ai", "ml", "government", "sovereign ai", "gpu", "data engineering"],
        "region": "India", "size_label": "SMALL", "employees": 80, "internal_tech_strength": 0.7,
    },
]

MATCH_THRESHOLD = 0.35


# ---------------------------------------------------
# SCORING HELPERS
# ---------------------------------------------------

def _keyword_overlap_score(query_text: str, keywords: list) -> float:
    """How much of the query text is actually about this company's space."""
    q = (query_text or "").lower()
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw in q)
    return round(min(1.0, hits / max(1, len(keywords) // 2)), 3)


def _region_fit(candidate_region: str, target_regions: list) -> float:
    if not target_regions:
        return 0.7
    if candidate_region in target_regions:
        return 0.9
    if candidate_region == "GLOBAL":
        return 0.7
    return 0.4


def _size_fit(size_label: str, preferred_sizes: list) -> float:
    if not preferred_sizes:
        return 0.7
    normalized = [s.upper() for s in preferred_sizes]
    return 0.9 if size_label in normalized else 0.5


# ---------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------

def run(query: str, deal_profile: dict | None = None):
    """
    Discover candidate companies matching the user's natural-language query
    and (optional) deal profile.

    Args:
        query: natural-language description of the target, e.g.
               "mid-size fintech and AI SaaS companies in India looking for
               data engineering and cloud modernization"
        deal_profile: optional dict with keys target_regions,
                      preferred_company_sizes (matches models.DealProfile)

    Returns:
        List of CandidateCompany, ranked by initial_match_score (best first).
    """
    deal_profile = deal_profile or {}
    target_regions = list(deal_profile.get("target_regions", []) or [])
    preferred_sizes = list(deal_profile.get("preferred_company_sizes", []) or [])

    results = []
    for entry in CANDIDATE_UNIVERSE:
        industry_fit = _keyword_overlap_score(query, entry["keywords"])
        geo_fit = _region_fit(entry["region"], target_regions)
        size_fit = _size_fit(entry["size_label"], preferred_sizes)
        internal_strength = entry["internal_tech_strength"]
        capability_gap = round(1 - internal_strength, 3)  # room for DataVex to add value

        initial_match_score = round(
            0.45 * industry_fit + 0.25 * geo_fit + 0.15 * size_fit + 0.15 * capability_gap, 3
        )

        c = CandidateCompany(
            company_name=entry["company_name"],
            domain=entry["domain"],
            industry=entry["industry"],
            size=entry["size_label"],
            estimated_employees=entry["employees"],
            region=entry["region"],
            capability_score=capability_gap,
            size_fit=size_fit,
            geo_fit=geo_fit,
            industry_fit=industry_fit,
            initial_match_score=initial_match_score,
            internal_tech_strength=internal_strength,
            conversion_bias=0.0,
            conversion_score=0.0,
            notes="Matched via keyword/region/size heuristics against the query.",
        )
        results.append(c)

    results.sort(key=lambda c: c.initial_match_score, reverse=True)

    filtered = [c for c in results if c.initial_match_score >= MATCH_THRESHOLD]
    if not filtered and results:
        # Nothing cleared the relevance bar — surface the single closest
        # match rather than silently returning an empty pipeline.
        filtered = results[:1]
        logger.info("No candidates above threshold %.2f — falling back to best match", MATCH_THRESHOLD)

    return filtered[:5]
