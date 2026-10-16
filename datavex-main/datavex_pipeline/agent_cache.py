"""
DataVex — Agent Output Cache
Per-company cache with timestamps, TTL, and source tracking (rules vs LLM).

Cache file: datavex_pipeline/agent_cache.json
TTL: 24 hours (CACHE_TTL_HOURS)
"""
import json
import os
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("datavex.cache")

CACHE_TTL_HOURS = 24
_CACHE_PATH = os.path.join(os.path.dirname(__file__), "agent_cache.json")


# ── Internal load/save ───────────────────────────────────────────

def _load() -> dict:
    if not os.path.exists(_CACHE_PATH):
        return {}
    try:
        with open(_CACHE_PATH) as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Cache read failed: %s", e)
        return {}


def _save(data: dict):
    try:
        with open(_CACHE_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning("Cache write failed: %s", e)


# ── Public API ───────────────────────────────────────────────────

def get_cached(company_name: str, agent_key: str) -> dict | None:
    """
    Return cached agent output for a company, or None if missing/stale.

    agent_key: e.g. "agent2", "agent3", "agent5", "agent6"
    """
    cache = _load()
    entry = cache.get(company_name, {})
    if not entry:
        return None

    # Check TTL
    ts_str = entry.get("timestamp")
    if ts_str:
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - ts
            if age > timedelta(hours=CACHE_TTL_HOURS):
                logger.debug("Cache stale for %s (%s)", company_name, agent_key)
                return None
        except Exception:
            return None

    return entry.get(agent_key)


def set_cached(
    company_name: str,
    agent_key: str,
    data: dict,
    sources: dict | None = None,
):
    """
    Write agent output to cache.

    sources: optional dict mapping field names → "rules" | "ollama" | "rag+ollama"
    Example: {"signals": "rules", "llm_confidence": "ollama"}
    """
    cache = _load()
    if company_name not in cache:
        cache[company_name] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": {},
        }
    # Refresh timestamp if writing a new agent key
    cache[company_name]["timestamp"] = datetime.now(timezone.utc).isoformat()
    cache[company_name][agent_key] = data

    if sources:
        existing_sources = cache[company_name].get("sources", {})
        for field, src in sources.items():
            existing_sources[f"{agent_key}.{field}"] = src
        cache[company_name]["sources"] = existing_sources

    _save(cache)


def invalidate(company_name: str):
    """
    Force cache invalidation for a company — forces full re-run.
    """
    cache = _load()
    if company_name in cache:
        del cache[company_name]
        _save(cache)
        logger.info("Cache invalidated for %s", company_name)


def invalidate_all():
    """Clear entire cache."""
    _save({})
    logger.info("Full cache cleared")


def get_full_entry(company_name: str) -> dict:
    """Return the entire cache entry for a company (all agents + metadata)."""
    return _load().get(company_name, {})


def is_fresh(company_name: str) -> bool:
    """Check if any cached data exists and is within TTL."""
    return get_cached(company_name, "agent2") is not None


def cache_summary() -> dict:
    """Return a summary of cached companies + their ages."""
    cache = _load()
    now   = datetime.now(timezone.utc)
    result = {}
    for name, entry in cache.items():
        ts_str = entry.get("timestamp", "")
        try:
            ts  = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_h = (now - ts).total_seconds() / 3600
            stale = age_h > CACHE_TTL_HOURS
        except Exception:
            age_h = 999
            stale = True
        agents = [k for k in entry if k not in ("timestamp", "sources")]
        result[name] = {"age_hours": round(age_h, 1), "stale": stale, "agents": agents}
    return result
