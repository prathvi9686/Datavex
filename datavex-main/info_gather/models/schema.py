from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    id         = Column(Integer, primary_key=True)
    name       = Column(String(255), unique=True)
    domain     = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EarningsTranscript(Base):
    __tablename__ = "earnings_transcripts"
    id           = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    quarter      = Column(String(20))
    raw_text     = Column(Text)
    source_url   = Column(Text)
    scraped_at   = Column(DateTime, default=datetime.utcnow)

class InvestorPresentation(Base):
    __tablename__ = "investor_presentations"
    id           = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    title        = Column(Text)
    raw_text     = Column(Text)
    pdf_url      = Column(Text)
    scraped_at   = Column(DateTime, default=datetime.utcnow)

class JobPosting(Base):
    __tablename__ = "job_postings"
    id           = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    role_title   = Column(String(255))
    department   = Column(String(100))
    description  = Column(Text)
    keywords     = Column(JSON)
    posted_date  = Column(String(50))
    source       = Column(String(100))
    scraped_at   = Column(DateTime, default=datetime.utcnow)

class PressRelease(Base):
    __tablename__ = "press_releases"
    id             = Column(Integer, primary_key=True)
    company_name   = Column(String(255))
    title          = Column(Text)
    content        = Column(Text)
    published_date = Column(String(50))
    source_url     = Column(Text)
    scraped_at     = Column(DateTime, default=datetime.utcnow)

class TechStack(Base):
    __tablename__ = "tech_stacks"
    id           = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    domain       = Column(String(255))
    frameworks   = Column(JSON)
    languages    = Column(JSON)
    raw_headers  = Column(JSON)
    debt_signals = Column(JSON)
    scraped_at   = Column(DateTime, default=datetime.utcnow)

class GithubData(Base):
    __tablename__ = "github_data"
    id                = Column(Integer, primary_key=True)
    company_name      = Column(String(255))
    org_name          = Column(String(255))
    total_repos       = Column(Integer)
    total_open_issues = Column(Integer)
    avg_commit_freq   = Column(Float)
    languages         = Column(JSON)
    legacy_signals    = Column(JSON)
    scraped_at        = Column(DateTime, default=datetime.utcnow)

class CustomerReview(Base):
    __tablename__ = "customer_reviews"
    id           = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    platform     = Column(String(50))
    review_text  = Column(Text)
    rating       = Column(Float)
    keywords     = Column(JSON)
    scraped_at   = Column(DateTime, default=datetime.utcnow)

class FinancialData(Base):
    __tablename__ = "financial_data"
    id               = Column(Integer, primary_key=True)
    company_name     = Column(String(255))
    ticker           = Column(String(20))
    quarter          = Column(String(20))
    revenue          = Column(Float)
    operating_margin = Column(Float)
    gross_margin     = Column(Float)
    net_income       = Column(Float)
    source           = Column(String(100))
    scraped_at       = Column(DateTime, default=datetime.utcnow)

class LayoffEvent(Base):
    __tablename__ = "layoff_events"
    id           = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    date         = Column(String(50))
    headcount    = Column(Integer, nullable=True)
    percentage   = Column(Float, nullable=True)
    source_url   = Column(Text)
    scraped_at   = Column(DateTime, default=datetime.utcnow)

class FundingRound(Base):
    __tablename__ = "funding_rounds"
    id           = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    round_type   = Column(String(50))
    amount_usd   = Column(Float, nullable=True)
    date         = Column(String(50))
    investors    = Column(JSON)
    source_url   = Column(Text)
    scraped_at   = Column(DateTime, default=datetime.utcnow)


def get_engine(db_url: str | None = None):
    url = db_url or os.getenv("DATABASE_URL", "sqlite:///datavex.db")
    # Supabase / any postgresql:// URL needs the psycopg3 driver prefix
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, echo=False)

def init_db(db_url: str | None = None):
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
