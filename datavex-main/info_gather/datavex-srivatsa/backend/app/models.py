"""
DataVex Backend — Pydantic Schemas
Request / response models for the REST API.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Scan ────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    query: str = Field(..., description="Natural language request, e.g. 'Analyze Meridian Systems'")
    sources: list[str] = Field(
        default=["github", "web", "news"],
        description="Data sources to scrape"
    )
    depth: str = Field(default="full", description="Scan depth: quick | full")


class ScanResponse(BaseModel):
    scan_id: str
    status: str
    estimated_duration_seconds: int = 120


class ScanStatusResponse(BaseModel):
    scan_id: str
    status: str
    progress: float
    company_name: Optional[str] = None
    agents_completed: list[str] = []
    agents_pending: list[str] = []
    error_message: Optional[str] = None


# ── Company (Lead Board) ───────────────────────────────────

class DecisionMakerSummary(BaseModel):
    name: str
    role: str


class StrongestMatchSummary(BaseModel):
    score: int
    capability: str
    pain: str


class CompanyListItem(BaseModel):
    id: str
    name: str
    descriptor: str
    score: int
    confidence: str
    coverage: int
    receptivity: str
    pain_tags: list[str] = []
    decision_maker: Optional[DecisionMakerSummary] = None
    strongest_match: Optional[StrongestMatchSummary] = None
    updated_at: Optional[str] = None


class CompanyListResponse(BaseModel):
    data: list[CompanyListItem]
    total: int
    limit: int = 50
    offset: int = 0


# ── Full Company Detail ────────────────────────────────────

class CompanyDetailResponse(BaseModel):
    """Full intelligence report — matches API contract schema."""
    id: str
    name: str
    score: int
    confidence: str
    coverage: int
    receptivity: str
    descriptor: str = ""
    financials: dict = {}
    hiring: list[dict] = []
    score_breakdown: list[dict] = []
    timeline: list[dict] = []
    pain_clusters: list[dict] = []
    decision_maker: dict = {}
    outreach: dict = {}
    capability_match: list[dict] = []
    strongest_match: dict = {}
    trace: list[dict] = []


# ── Capability ─────────────────────────────────────────────

class CapabilityItem(BaseModel):
    id: str
    name: str
    score: int
    description: str


class CapabilitiesResponse(BaseModel):
    data: list[CapabilityItem]


# ── Capability Match ───────────────────────────────────────

class CapabilityMatchResponse(BaseModel):
    company_id: str
    strongest_match: dict = {}
    matches: list[dict] = []


# ── Trace ──────────────────────────────────────────────────

class TraceEntry(BaseModel):
    time: str
    agent: str
    action: str


class TraceResponse(BaseModel):
    company_id: str
    verdict: str = ""
    recommended_persona: str = ""
    window: str = ""
    trace: list[TraceEntry] = []


# ── System ─────────────────────────────────────────────────

class SystemStatusResponse(BaseModel):
    status: str = "online"
    version: str = "2.4.1"
    synth_layer: str = "active"
    agents: dict = {}
    last_scan: Optional[str] = None


# ── Error ──────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    code: str = ""
    details: dict = {}
