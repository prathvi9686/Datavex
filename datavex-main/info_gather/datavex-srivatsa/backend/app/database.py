"""
DataVex Backend — Database Layer
SQLAlchemy engine + session factory.
Uses Supabase PostgreSQL if configured, falls back to local SQLite.
Creates tables on startup.
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Text,
    DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_db_url() -> str:
    """
    Determine database URL.
    Falls back to SQLite if Supabase connection string has placeholder password.
    """
    url = settings.database_url
    if "[YOUR-PASSWORD]" in url or url == "sqlite:///./datavex.db":
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datavex.db")
        fallback = f"sqlite:///{db_path}"
        logger.warning(f"Supabase password not configured — using local SQLite: {db_path}")
        return fallback
    return url


db_url = _get_db_url()
is_sqlite = db_url.startswith("sqlite")

engine_kwargs = {"pool_pre_ping": True}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── ORM Models ──────────────────────────────────────────────

class ScanRecord(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=new_uuid)
    user_request = Column(Text, nullable=False)
    status = Column(String, default="queued")  # queued | running | completed | failed
    progress = Column(Float, default=0.0)
    company_name = Column(String, nullable=True)
    agents_completed = Column(JSON, default=list)
    agents_pending = Column(JSON, default=list)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)


class CompanyRecord(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)   # slug, e.g. "meridian-systems"
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    name = Column(String, nullable=False)
    descriptor = Column(String, nullable=True)
    score = Column(Integer, default=0)
    confidence = Column(String, default="LOW")
    coverage = Column(Integer, default=0)
    data = Column(JSON, default=dict)       # full intelligence report blob
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow)


class AgentTraceRecord(Base):
    __tablename__ = "agent_traces"

    id = Column(String, primary_key=True, default=new_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    agent = Column(String, nullable=False)
    action = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=utcnow)


# ── Helpers ─────────────────────────────────────────────────

def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized ({'SQLite' if is_sqlite else 'PostgreSQL'})")


def get_db() -> Session:
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
