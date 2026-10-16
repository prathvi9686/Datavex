"""
DataVex AI — Backend API Server
FastAPI application with CORS, database init, and router registration.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import scan, companies, system

# ── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-28s │ %(levelname)-5s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── App ─────────────────────────────────────────────────────
app = FastAPI(
    title="DataVex AI",
    description="Multi-agent sales intelligence platform API",
    version="2.4.1",
)

# CORS — allow the Vite frontend (port 5173) and any local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ─────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    logger.info("DataVex Backend starting...")
    init_db()
    logger.info("Database tables initialized")
    logger.info("DataVex Backend ready")


# ── Register Routers ────────────────────────────────────────
app.include_router(scan.router)
app.include_router(companies.router)
app.include_router(system.router)


# ── Root ────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "name": "DataVex AI",
        "version": "2.4.1",
        "docs": "/docs",
        "status": "online",
    }
