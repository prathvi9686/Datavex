"""
DataVex Backend — Scan Router
POST /scan — trigger intelligence scan
GET /scan/:id — check scan progress
"""
import asyncio
import threading
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db, ScanRecord, SessionLocal, new_uuid, utcnow
from app.models import ScanRequest, ScanResponse, ScanStatusResponse
from app.agents.orchestrator import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["scan"])


def _run_pipeline_in_thread(scan_id: str, user_request: str):
    """
    Run the async pipeline in a separate thread with its own event loop
    and DB session (background tasks can't share the request's session).
    """
    db = SessionLocal()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_pipeline(scan_id, user_request, db))
        loop.close()
    except Exception as e:
        logger.error(f"Pipeline thread error: {e}", exc_info=True)
        scan = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
        if scan:
            scan.status = "failed"
            scan.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/scan", response_model=ScanResponse)
def trigger_scan(req: ScanRequest, db: Session = Depends(get_db)):
    """
    Trigger a full intelligence scan.
    Launches the agent pipeline in a background thread.
    """
    scan_id = new_uuid()

    scan = ScanRecord(
        id=scan_id,
        user_request=req.query,
        status="queued",
        progress=0.0,
        created_at=utcnow(),
    )
    db.add(scan)
    db.commit()

    # Launch pipeline in background thread
    thread = threading.Thread(
        target=_run_pipeline_in_thread,
        args=(scan_id, req.query),
        daemon=True,
    )
    thread.start()

    logger.info(f"Scan {scan_id} queued for: '{req.query}'")

    return ScanResponse(
        scan_id=scan_id,
        status="queued",
        estimated_duration_seconds=120,
    )


@router.get("/scan/{scan_id}", response_model=ScanStatusResponse)
def get_scan_status(scan_id: str, db: Session = Depends(get_db)):
    """Check the status of a running scan."""
    scan = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanStatusResponse(
        scan_id=scan.id,
        status=scan.status,
        progress=scan.progress or 0.0,
        company_name=scan.company_name,
        agents_completed=scan.agents_completed or [],
        agents_pending=scan.agents_pending or [],
        error_message=scan.error_message,
    )
