"""
DataVex Backend — Companies Router
GET /companies — list all analyzed companies
GET /companies/:id — full intelligence report
GET /companies/:id/capability-match — capability match
GET /companies/:id/trace — reasoning trace
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db, CompanyRecord, AgentTraceRecord
from app.models import (
    CompanyListResponse, CompanyListItem, CompanyDetailResponse,
    CapabilityMatchResponse, TraceResponse, TraceEntry,
    DecisionMakerSummary, StrongestMatchSummary,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["companies"])


@router.get("/companies", response_model=CompanyListResponse)
def list_companies(
    sort_by: str = Query("score", description="Sort field"),
    order: str = Query("desc", description="Sort order"),
    confidence: str | None = Query(None, description="Filter by confidence"),
    min_score: int | None = Query(None, description="Min opportunity score"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all tracked target companies with summary data."""
    query = db.query(CompanyRecord)

    # Filters
    if confidence:
        query = query.filter(CompanyRecord.confidence == confidence.upper())
    if min_score is not None:
        query = query.filter(CompanyRecord.score >= min_score)

    # Sort
    sort_col = getattr(CompanyRecord, sort_by, CompanyRecord.score)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    total = query.count()
    companies = query.offset(offset).limit(limit).all()

    items = []
    for c in companies:
        data = c.data or {}

        # Extract decision maker summary
        dm = data.get("decisionMaker") or data.get("decision_maker") or {}
        dm_summary = None
        if dm.get("name"):
            dm_summary = DecisionMakerSummary(name=dm["name"], role=dm.get("role", ""))

        # Extract strongest match summary
        sm = data.get("strongestMatch") or data.get("strongest_match") or {}
        sm_summary = None
        if sm.get("capability"):
            sm_summary = StrongestMatchSummary(
                score=sm.get("score", 0),
                capability=sm["capability"],
                pain=sm.get("pain", ""),
            )

        items.append(CompanyListItem(
            id=c.id,
            name=c.name,
            descriptor=c.descriptor or data.get("descriptor", ""),
            score=c.score,
            confidence=c.confidence,
            coverage=c.coverage,
            receptivity=data.get("receptivity", ""),
            pain_tags=data.get("painTags") or data.get("pain_tags", []),
            decision_maker=dm_summary,
            strongest_match=sm_summary,
            updated_at=c.updated_at.isoformat() if c.updated_at else None,
            competitor=data.get("competitor", False),
            data={
                "competitor": data.get("competitor", False),
                "competitor_note": data.get("competitor_note", ""),
                "signal_counts": data.get("signal_counts", {}),
                "pain_level": data.get("pain_level", ""),
                "agent4": data.get("agent4", {}),
                "agent5": data.get("agent5", {}),
            },
        ))

    return CompanyListResponse(data=items, total=total, limit=limit, offset=offset)


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
def get_company(company_id: str, db: Session = Depends(get_db)):
    """Full intelligence report for a single company."""
    company = db.query(CompanyRecord).filter(CompanyRecord.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    data = company.data or {}

    return CompanyDetailResponse(
        id=company.id,
        name=company.name,
        score=company.score,
        confidence=company.confidence,
        coverage=company.coverage,
        descriptor=company.descriptor or data.get("descriptor", ""),
        receptivity=data.get("receptivity", ""),
        financials=data.get("financials", {}),
        hiring=data.get("hiring", []),
        score_breakdown=data.get("scoreBreakdown") or data.get("score_breakdown", []),
        timeline=data.get("timeline", []),
        pain_clusters=data.get("painClusters") or data.get("pain_clusters", []),
        decision_maker=data.get("decisionMaker") or data.get("decision_maker", {}),
        outreach=data.get("outreach", {}),
        capability_match=data.get("capabilityMatch") or data.get("capability_match", []),
        strongest_match=data.get("strongestMatch") or data.get("strongest_match", {}),
        trace=data.get("trace", []),
        pain_level=data.get("pain_level", ""),
        pain_tags=data.get("pain_tags") or data.get("painTags", []),
        agent1=data.get("agent1", {}),
        agent2=data.get("agent2", {}),
        agent3=data.get("agent3", {}),
        agent35=data.get("agent35", {}),
        agent4=data.get("agent4", {}),
        agent5=data.get("agent5", {}),
        competitor=data.get("competitor", False),
        competitor_note=data.get("competitor_note", ""),
        signal_counts=data.get("signal_counts", {}),
    )


@router.get("/companies/{company_id}/capability-match", response_model=CapabilityMatchResponse)
def get_capability_match(company_id: str, db: Session = Depends(get_db)):
    """Capability match analysis for a company."""
    company = db.query(CompanyRecord).filter(CompanyRecord.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    data = company.data or {}
    cap_matches = data.get("capabilityMatch") or data.get("capability_match", [])
    strongest = data.get("strongestMatch") or data.get("strongest_match", {})

    # Group matches by capability
    grouped = {}
    for m in cap_matches:
        cap = m.get("capability", "Unknown")
        if cap not in grouped:
            grouped[cap] = {"capability": cap, "capability_score": 0, "matched_pains": []}
        grouped[cap]["matched_pains"].append({
            "pain": m.get("pain", ""),
            "source": m.get("source", ""),
            "severity": m.get("severity", ""),
        })

    return CapabilityMatchResponse(
        company_id=company_id,
        strongest_match=strongest,
        matches=list(grouped.values()),
    )


@router.get("/companies/{company_id}/trace", response_model=TraceResponse)
def get_trace(company_id: str, db: Session = Depends(get_db)):
    """Agent reasoning trace for a company."""
    company = db.query(CompanyRecord).filter(CompanyRecord.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    data = company.data or {}
    trace = data.get("trace", [])

    # Get decision info from the last trace entry
    verdict = data.get("confidence", "")
    dm = data.get("decisionMaker") or data.get("decision_maker", {})
    recommended_persona = dm.get("role", "")

    return TraceResponse(
        company_id=company_id,
        verdict=verdict,
        recommended_persona=recommended_persona,
        window="",
        trace=[
            TraceEntry(
                time=t.get("time", ""),
                agent=t.get("agent", ""),
                action=t.get("action", ""),
            )
            for t in trace
        ],
    )
