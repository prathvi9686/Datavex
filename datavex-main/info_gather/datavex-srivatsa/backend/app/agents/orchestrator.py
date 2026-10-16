"""
DataVex Backend — Agent Orchestrator
Runs the 7-agent pipeline sequentially, tracks progress, stores results.
"""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import ScanRecord, CompanyRecord, AgentTraceRecord, new_uuid, utcnow
from app.agents import (
    prompt_agent,
    research_agent,
    finance_agent,
    tech_agent,
    conflict_agent,
    synthesis_agent,
    decision_agent,
)

logger = logging.getLogger(__name__)

ALL_AGENTS = [
    "PROMPT_AGENT",
    "RESEARCH_AGENT",
    "FINANCE_AGENT",
    "TECH_AGENT",
    "CONFLICT_AGENT",
    "SYNTHESIS_AGENT",
    "DECISION_AGENT",
]


def _add_trace(db: Session, scan_id: str, agent: str, action: str):
    """Log an agent action to the trace table."""
    trace = AgentTraceRecord(
        id=new_uuid(),
        scan_id=scan_id,
        agent=agent,
        action=action,
        timestamp=utcnow(),
    )
    db.add(trace)
    db.commit()


def _update_scan_progress(db: Session, scan: ScanRecord, completed: list[str]):
    """Update scan progress based on completed agents."""
    scan.agents_completed = completed
    scan.agents_pending = [a for a in ALL_AGENTS if a not in completed]
    scan.progress = len(completed) / len(ALL_AGENTS)
    db.commit()


async def run_pipeline(scan_id: str, user_request: str, db: Session):
    """
    Execute the full 7-agent intelligence pipeline.
    This runs as a background task.
    """
    logger.info(f"ORCHESTRATOR: starting pipeline for scan {scan_id}")

    # Get scan record
    scan = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
    if not scan:
        logger.error(f"Scan {scan_id} not found")
        return

    scan.status = "running"
    scan.agents_pending = ALL_AGENTS.copy()
    db.commit()

    completed = []

    try:
        # ── 1. PROMPT AGENT ─────────────────────────────────────
        _add_trace(db, scan_id, "PROMPT_AGENT", f"processing request: '{user_request}'")
        plan = await prompt_agent.run(user_request)
        completed.append("PROMPT_AGENT")
        _update_scan_progress(db, scan, completed)
        _add_trace(db, scan_id, "PROMPT_AGENT", f"plan ready: {plan.get('company_name', 'Unknown')} — {len(plan.get('web_queries', []))} queries")

        company_name = plan.get("company_name", "Unknown")
        company_slug = plan.get("company_slug", "unknown")
        scan.company_name = company_name
        db.commit()

        # ── 2. RESEARCH AGENT ───────────────────────────────────
        _add_trace(db, scan_id, "RESEARCH_AGENT", f"scraping data for '{company_name}'")
        raw_data = await research_agent.run(plan)
        completed.append("RESEARCH_AGENT")
        _update_scan_progress(db, scan, completed)
        _add_trace(
            db, scan_id, "RESEARCH_AGENT",
            f"collected {len(raw_data.get('github_repos', []))} repos, "
            f"{len(raw_data.get('github_issues', []))} issues, "
            f"{len(raw_data.get('web_results', []))} web results"
        )

        # ── 3. FINANCE AGENT ────────────────────────────────────
        _add_trace(db, scan_id, "FINANCE_AGENT", f"analyzing financial signals for '{company_name}'")
        finance_data = await finance_agent.run(raw_data)
        completed.append("FINANCE_AGENT")
        _update_scan_progress(db, scan, completed)
        _add_trace(
            db, scan_id, "FINANCE_AGENT",
            f"detected {len(finance_data.get('financial_signals', []))} financial signals"
        )

        # ── 4. TECH AGENT ───────────────────────────────────────
        _add_trace(db, scan_id, "TECH_AGENT", f"analyzing tech signals for '{company_name}'")
        tech_data = await tech_agent.run(raw_data)
        completed.append("TECH_AGENT")
        _update_scan_progress(db, scan, completed)
        _add_trace(
            db, scan_id, "TECH_AGENT",
            f"{len(tech_data.get('pain_clusters', []))} pain clusters, "
            f"{len(tech_data.get('hiring', []))} hiring signals"
        )

        # ── 5. CONFLICT AGENT ───────────────────────────────────
        _add_trace(db, scan_id, "CONFLICT_AGENT", f"checking contradictions for '{company_name}'")
        conflict_data = await conflict_agent.run(finance_data, tech_data, company_name)
        completed.append("CONFLICT_AGENT")
        _update_scan_progress(db, scan, completed)
        _add_trace(
            db, scan_id, "CONFLICT_AGENT",
            f"found {len(conflict_data.get('contradictions', []))} contradictions — tension: {conflict_data.get('overall_tension', 'N/A')}"
        )

        # ── 6. SYNTHESIS AGENT ──────────────────────────────────
        _add_trace(db, scan_id, "SYNTHESIS_AGENT", f"building unified narrative for '{company_name}'")
        synthesis_data = await synthesis_agent.run(
            finance_data, tech_data, conflict_data, raw_data, company_name
        )
        completed.append("SYNTHESIS_AGENT")
        _update_scan_progress(db, scan, completed)
        _add_trace(
            db, scan_id, "SYNTHESIS_AGENT",
            f"narrative built — {len(synthesis_data.get('timeline', []))} timeline events, "
            f"{len(synthesis_data.get('capability_match', []))} capability matches"
        )

        # ── 7. DECISION AGENT ───────────────────────────────────
        _add_trace(db, scan_id, "DECISION_AGENT", f"issuing verdict for '{company_name}'")
        decision_data = await decision_agent.run(
            finance_data, tech_data, conflict_data, synthesis_data, company_name
        )
        completed.append("DECISION_AGENT")
        _update_scan_progress(db, scan, completed)
        _add_trace(
            db, scan_id, "DECISION_AGENT",
            f"verdict: {decision_data.get('verdict', 'N/A')}. "
            f"Score: {decision_data.get('score', 0)}. "
            f"Window: {decision_data.get('window', 'N/A')}. "
            f"Recommended persona: {decision_data.get('recommended_persona', 'N/A')}."
        )

        # ── ASSEMBLE FINAL REPORT ───────────────────────────────
        # Get traces for this scan
        traces = db.query(AgentTraceRecord).filter(
            AgentTraceRecord.scan_id == scan_id
        ).order_by(AgentTraceRecord.timestamp).all()

        trace_list = [
            {
                "time": t.timestamp.strftime("%Y.%m.%d %H:%M:%S") if t.timestamp else "",
                "agent": t.agent,
                "action": t.action,
            }
            for t in traces
        ]

        full_report = {
            "id": company_slug,
            "name": company_name,
            "descriptor": synthesis_data.get("descriptor", ""),
            "score": decision_data.get("score", 0),
            "confidence": decision_data.get("confidence", "MEDIUM"),
            "coverage": decision_data.get("coverage", 50),
            "receptivity": synthesis_data.get("receptivity", "MEDIUM — MONITOR"),
            "painTags": synthesis_data.get("pain_tags", []),
            "financials": finance_data.get("financials", {}),
            "hiring": tech_data.get("hiring", []),
            "scoreBreakdown": decision_data.get("score_breakdown", []),
            "timeline": synthesis_data.get("timeline", []),
            "painClusters": synthesis_data.get("pain_clusters", []) or tech_data.get("pain_clusters", []),
            "decisionMaker": synthesis_data.get("decision_maker", {}),
            "outreach": synthesis_data.get("outreach", {}),
            "capabilityMatch": synthesis_data.get("capability_match", []),
            "strongestMatch": synthesis_data.get("strongest_match", {}),
            "trace": trace_list,
        }

        # ── SAVE TO DATABASE ────────────────────────────────────
        existing = db.query(CompanyRecord).filter(CompanyRecord.id == company_slug).first()
        if existing:
            existing.data = full_report
            existing.score = decision_data.get("score", 0)
            existing.confidence = decision_data.get("confidence", "MEDIUM")
            existing.coverage = decision_data.get("coverage", 50)
            existing.descriptor = synthesis_data.get("descriptor", "")
            existing.scan_id = scan_id
            existing.updated_at = utcnow()
        else:
            company = CompanyRecord(
                id=company_slug,
                scan_id=scan_id,
                name=company_name,
                descriptor=synthesis_data.get("descriptor", ""),
                score=decision_data.get("score", 0),
                confidence=decision_data.get("confidence", "MEDIUM"),
                coverage=decision_data.get("coverage", 50),
                data=full_report,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(company)

        # Mark scan as completed
        scan.status = "completed"
        scan.progress = 1.0
        scan.completed_at = utcnow()
        scan.agents_completed = ALL_AGENTS.copy()
        scan.agents_pending = []
        db.commit()

        logger.info(f"ORCHESTRATOR: pipeline completed for '{company_name}' — score: {decision_data.get('score', 0)}")

    except Exception as e:
        logger.error(f"ORCHESTRATOR: pipeline failed for scan {scan_id}: {e}", exc_info=True)
        scan.status = "failed"
        scan.error_message = str(e)
        scan.agents_completed = completed
        scan.agents_pending = [a for a in ALL_AGENTS if a not in completed]
        db.commit()
        _add_trace(db, scan_id, "ORCHESTRATOR", f"pipeline failed: {str(e)}")
