from pydantic import BaseModel
from typing import Optional, List


# ─────────────────────────────────────────────
# USER INPUT
# ─────────────────────────────────────────────

class UserIntent(BaseModel):
    raw_text: str


class DealProfile(BaseModel):
    min_deal_usd: int
    max_deal_usd: int
    target_regions: List[str]
    preferred_company_sizes: List[str]


# ─────────────────────────────────────────────
# AGENT 1 — DISCOVERY OUTPUT
# ─────────────────────────────────────────────

class CandidateCompany(BaseModel):
    company_name: str
    domain: str
    industry: str
    size: str
    estimated_employees: int
    region: str

    capability_score: float = 0.0
    size_fit: float = 0.0
    geo_fit: float = 0.0
    industry_fit: float = 0.0

    # REQUIRED by pipeline
    initial_match_score: float = 0.0
    internal_tech_strength: float = 0.0
    conversion_bias: float = 0.0
    conversion_score: float = 0.0

    notes: str = ""


# ─────────────────────────────────────────────
# AGENT 2 — SIGNAL INPUT
# ─────────────────────────────────────────────

class SimpleCompany(BaseModel):
    company_name: str
    domain: str


class EvidenceItem(BaseModel):
    text: str
    source: str
    recency_days: Optional[int] = None


# ─────────────────────────────────────────────
# AGENT 3 — FINAL OUTPUT STRUCTURE
# ─────────────────────────────────────────────

class OpportunityScore(BaseModel):
    company_name: str
    opportunity_score: float
    priority: str
    timing_window: str
    company_state: str
    capability_alignment: float
    urgency_score: float
    strategic_summary: str
    why_we_win: List[str] = []
    risks: List[str] = []
    confidence: float = 0.0