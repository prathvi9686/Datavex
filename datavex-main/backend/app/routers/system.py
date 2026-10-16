"""
DataVex Backend — System Router
GET /system/status — health check
GET /capabilities — platform capabilities
"""
import logging
from fastapi import APIRouter
from app.models import SystemStatusResponse, CapabilitiesResponse, CapabilityItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["system"])

# DataVex platform capabilities (static)
CAPABILITIES = [
    CapabilityItem(
        id="pipeline-repair",
        name="Real-Time Pipeline Repair",
        score=96,
        description="Automated detection and self-healing of broken data connectors. Reduces MTTR from hours to minutes.",
    ),
    CapabilityItem(
        id="legacy-migration",
        name="Legacy Stack Migration",
        score=84,
        description="Structured migration from monolithic warehouses to composable architectures with zero-downtime cutover.",
    ),
    CapabilityItem(
        id="schema-evolution",
        name="Schema Evolution Management",
        score=88,
        description="Automatic schema drift detection and downstream contract enforcement.",
    ),
    CapabilityItem(
        id="observability",
        name="Data Observability Layer",
        score=91,
        description="End-to-end lineage tracking, anomaly detection, and SLA alerting across all pipeline stages.",
    ),
    CapabilityItem(
        id="vector-search",
        name="Vector Search Infrastructure",
        score=73,
        description="Production-grade embedding pipelines and vector index management for AI-native data products.",
    ),
]


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status():
    """Platform health check."""
    return SystemStatusResponse(
        status="online",
        version="2.4.1",
        synth_layer="active",
        agents={
            "prompt": "online",
            "research": "online",
            "finance": "online",
            "tech": "online",
            "conflict": "online",
            "synthesis": "online",
            "decision": "online",
        },
        last_scan=None,
    )


@router.get("/capabilities", response_model=CapabilitiesResponse)
def list_capabilities():
    """List DataVex platform capabilities."""
    return CapabilitiesResponse(data=CAPABILITIES)
