"""
DataVex Backend — Discovery Router
POST /discover — auto-discover target companies using the 5-agent pipeline.
Calls agents 1-5 directly (no orchestrator). Only one scan at a time.
"""
import sys
import os
import threading
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal, ScanRecord, CompanyRecord, new_uuid, utcnow

# ── Add datavex_pipeline to path ─────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
PIPELINE_DIR = os.path.join(PROJECT_ROOT, "datavex_pipeline")
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["discover"])

# ── Rate limiter: one scan at a time ─────────────────────────
_scan_lock = threading.Lock()
_active_scan_id = None


# ── Helpers ──────────────────────────────────────────────────

def _priority_to_confidence(priority: str) -> str:
    return {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}.get(priority, "LOW")


def _score_int(opportunity_score: float) -> int:
    return max(0, min(100, int(round(opportunity_score * 100))))


def _guess_domain(company_name: str) -> str:
    """Best-effort domain guess from company name."""
    slug = company_name.lower()
    slug = slug.replace("&", "and")
    import re
    slug = re.sub(r"[^a-z0-9]+", "", slug)
    return f"{slug}.com"


# ── Search-Discover pipeline runner ──────────────────────────

def _rich_scrape(company_name: str, domain: str) -> dict:
    """
    Full multi-source scraper with per-step 15s timeouts.
    Each scraper step runs in a thread — if it hangs, it's cancelled after timeout.
    Returns a search_cache.json-compatible entry dict.
    """
    import concurrent.futures
    import urllib.parse, urllib.request
    import xml.etree.ElementTree as ET
    from datetime import datetime, timezone

    signals: dict[str, list] = {"funding": [], "product": [], "infra": [], "careers": []}

    scraper_dir = os.path.join(PROJECT_ROOT, "info_gather", "datavex-srivatsa", "info_gather")
    if scraper_dir not in sys.path:
        sys.path.insert(0, scraper_dir)

    def _run_with_timeout(fn, *args, timeout=15):
        """Run fn(*args) in a thread; return None on timeout or error."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(fn, *args)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                logger.warning(f"⏰ Timeout ({timeout}s) on {fn.__name__} for {company_name}")
                return None
            except Exception as e:
                logger.warning(f"✗ {fn.__name__} failed for {company_name}: {e}")
                return None

    # ── 1. Tech stack ──────────────────────────────────────────
    logger.info(f"  [1/4] tech_stack → {domain}")
    try:
        from scrapers.tech_stack import detect_tech_stack
        tech = _run_with_timeout(detect_tech_stack, domain, company_name, timeout=15)
        if tech:
            fw = tech.get("frameworks", [])
            legacy = tech.get("debt_signals", {}).get("detected_legacy_tech", [])
            if fw:
                modern = [f for f in fw if f not in legacy]
                if modern:
                    signals["infra"].append({
                        "text": f"{company_name} runs on: {', '.join(modern[:5])}.",
                        "source": f"Tech stack — {domain}", "recency_days": 7,
                        "verified": True, "verification_source": f"https://{domain}",
                    })
            if legacy and len(legacy) >= 2:
                signals["infra"].append({
                    "text": f"Legacy stack detected: {', '.join(legacy[:3])}.",
                    "source": f"Tech stack — {domain}", "recency_days": 7,
                    "verified": True, "verification_source": f"https://{domain}",
                })
    except ImportError:
        logger.warning("  tech_stack scraper not available")

    # ── 2. Press releases / news ───────────────────────────────
    logger.info(f"  [2/4] press_releases → {company_name}")
    try:
        from scrapers.press_releases import scrape_press_releases
        articles = _run_with_timeout(scrape_press_releases, company_name, domain, None, 10, timeout=15)
        if articles:
            for a in articles[:6]:
                title = a.get("title", "")
                url   = a.get("source_url", "")
                if len(title) < 10:
                    continue
                signals["product"].append({
                    "text": title[:200], "source": url or "Google News",
                    "recency_days": 30, "verified": bool(url), "verification_source": url,
                })
    except ImportError:
        logger.warning("  press_releases scraper not available")

    # ── 3. Funding news ────────────────────────────────────────
    logger.info(f"  [3/4] funding_news → {company_name}")
    try:
        from scrapers.financials import scrape_funding_news, scrape_layoff_news
        funding = _run_with_timeout(scrape_funding_news, company_name, timeout=12)
        if funding:
            for f in funding[:4]:
                headline = f.get("headline", "") or f.get("title", "")
                if len(headline) > 10:
                    signals["funding"].append({
                        "text": headline[:200], "source": f.get("source_url", "Google News"),
                        "recency_days": 45, "verified": True,
                        "verification_source": f.get("source_url", ""),
                    })
        layoffs = _run_with_timeout(scrape_layoff_news, company_name, domain, timeout=10)
        if layoffs:
            for l in layoffs[:2]:
                headline = l.get("headline", "")
                if len(headline) > 10:
                    signals["infra"].append({
                        "text": headline[:200], "source": l.get("source_url", "Google News"),
                        "recency_days": 30, "verified": True,
                        "verification_source": l.get("source_url", ""),
                    })
    except ImportError:
        logger.warning("  financials scraper not available")

    # ── 4. RSS fallback if scrapers returned nothing ───────────
    total_signals = sum(len(v) for v in signals.values())
    if total_signals < 3:
        logger.info(f"  [4/4] RSS fallback (only {total_signals} signals so far)")
        for q in [f"{company_name} funding OR investment OR expansion",
                  f"{company_name} technology OR product OR AI"]:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-US&gl=US&ceid=US:en"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    root = ET.fromstring(resp.read())
                for item in root.findall(".//item")[:5]:
                    title = item.findtext("title") or ""
                    link  = item.findtext("link") or ""
                    if len(title) > 10:
                        signals["product"].append({
                            "text": title[:200], "source": link or "Google News RSS",
                            "recency_days": 30, "verified": bool(link),
                            "verification_source": link,
                        })
            except Exception as e:
                logger.warning(f"RSS fallback failed: {e}")

    signals = {k: v for k, v in signals.items() if v}
    total = sum(len(v) for v in signals.values())
    logger.info(f"  ✓ {total} signals collected for '{company_name}'")

    return {
        "meta": {
            "industry": "Unknown",
            "size": "MID",
            "region": "Unknown",
            "employees": 500,
            "competitor": False,
            "internal_tech_strength": 0.5,
            "conversion_bias": 0.65,
            "domain_display": company_name,
        },
        "signals": signals,
        "decision_makers": [{"name": "", "role": "CTO / VP Engineering"}],
    }


def _run_search_discover_pipeline(company_name: str, domain: str, scan_id: str):
    """
    Analyse a user-specified company with rich multi-source data, run agents 2-6,
    and save the result to DB. Runs in a background thread.
    Uses cached data if available, otherwise runs the full scraper with per-step timeouts.
    """
    global _active_scan_id
    import urllib.parse
    db = SessionLocal()
    try:
        scan = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
        if not scan:
            return

        scan.status       = "running"
        scan.progress     = 0.08
        scan.company_name = company_name
        scan.agents_pending   = ["DATA_COLLECTION", "SIGNALS", "SCORING", "DECISION", "RECOMMENDER", "OUTREACH"]
        scan.agents_completed = []
        db.commit()

        # ── Set up pipeline dir ────────────────────────────────
        pipeline_dir = PIPELINE_DIR
        if pipeline_dir not in sys.path:
            sys.path.insert(0, pipeline_dir)
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)

        # Purge stale module cache
        for mod in list(sys.modules.keys()):
            if mod.startswith(("agent", "config", "knowledge_base", "ollama_client")):
                del sys.modules[mod]

        # ── Step 1: Build/get rich signals ────────────────────
        cache_path = os.path.join(pipeline_dir, "search_cache.json")
        try:
            with open(cache_path) as f:
                cache_data = __import__("json").load(f)
        except Exception:
            cache_data = {}

        if company_name not in cache_data:
            logger.info(f"'{company_name}' not in search_cache — running full scrape with timeouts...")
            scraped = _rich_scrape(company_name, domain)
            cache_data[company_name] = scraped
            with open(cache_path, "w") as f:
                __import__("json").dump(cache_data, f, indent=2)
            total_sigs = sum(len(v) for v in scraped.get("signals", {}).values())
            logger.info(f"Scraped and cached {total_sigs} signals for '{company_name}'")
        else:
            logger.info(f"'{company_name}' found in search_cache — using cached rich data")

        scan.progress     = 0.35

        scan.agents_completed = ["DATA_COLLECTION"]
        scan.agents_pending   = ["SIGNALS", "SCORING", "DECISION", "RECOMMENDER", "OUTREACH"]
        db.commit()

        # ── Step 2–6: Run agents ─────────────────────────────
        import agent2_signals, agent3_scoring, agent4_decision_maker
        import agent5_outreach, agent6_recommender

        # Build candidate object with all fields agents need from cache metadata
        _meta = cache_data.get(company_name, {}).get("meta", {})
        _slug = company_name.lower().replace(" ", "-").replace(".", "")

        import types
        cand_obj = types.SimpleNamespace(
            company_name           = company_name,
            size                   = _meta.get("size", "MID"),
            internal_tech_strength = _meta.get("internal_tech_strength", 0.5),
            industry               = _meta.get("industry", "Unknown"),
            region                 = _meta.get("region", "Unknown"),
            employees              = _meta.get("employees", 500),
            domain                 = domain,
            slug                   = _slug,
        )
        cands    = [cand_obj]
        signals  = agent2_signals.run(cands)

        scan.progress     = 0.55
        scan.agents_completed = ["DATA_COLLECTION", "SIGNALS"]
        scan.agents_pending   = ["SCORING", "DECISION", "RECOMMENDER", "OUTREACH"]
        db.commit()

        scored    = agent3_scoring.run(cands, signals)
        decisions = agent4_decision_maker.run(scored)

        scan.progress     = 0.75
        scan.agents_completed = ["DATA_COLLECTION", "SIGNALS", "SCORING", "DECISION"]
        scan.agents_pending   = ["RECOMMENDER", "OUTREACH"]
        db.commit()

        recs     = agent6_recommender.run(decisions, signals)
        outreach = agent5_outreach.run(decisions, recs, signals)

        scan.progress     = 0.92
        scan.agents_completed = ["DATA_COLLECTION", "SIGNALS", "SCORING", "DECISION", "RECOMMENDER", "OUTREACH"]
        scan.agents_pending   = []
        db.commit()

        # ── Assemble & Save ───────────────────────────────────
        a2 = signals[0]   if signals   else {}
        a3 = scored[0]    if scored    else {}
        a4 = decisions[0] if decisions else {}
        a5 = outreach[0]  if outreach  else {}
        a6 = recs[0]      if recs      else {}

        opp_score = a3.get("opportunity_score", 0.5) if isinstance(a3, dict) else 0.5
        priority  = a3.get("priority", "LOW")         if isinstance(a3, dict) else "LOW"
        score_int_val = _score_int(opp_score)
        confidence    = _priority_to_confidence(priority)

        slug = company_name.lower().replace(" ", "-").replace(".", "")

        paint_level = a2.get("pain_level", "LOW")  if isinstance(a2, dict) else "LOW"
        key_signals = a3.get("key_signals", [])    if isinstance(a3, dict) else []
        intent      = a3.get("intent_score", 0.5)  if isinstance(a3, dict) else 0.5
        conv        = a3.get("conversion_score", 0.5) if isinstance(a3, dict) else 0.5
        deal_sz     = a3.get("deal_size_score", 0.5)  if isinstance(a3, dict) else 0.5
        expansion   = a3.get("expansion_score", 0.3)  if isinstance(a3, dict) else 0.3
        strategy    = a4.get("strategy", "MONITOR")   if isinstance(a4, dict) else "MONITOR"
        offer       = a4.get("recommended_offer", "") if isinstance(a4, dict) else ""
        entry_pt    = a4.get("entry_point", "")       if isinstance(a4, dict) else ""
        persona     = a5.get("persona", "")           if isinstance(a5, dict) else ""
        channel     = a5.get("channel", "")           if isinstance(a5, dict) else ""
        subject     = a5.get("subject", "")           if isinstance(a5, dict) else ""
        message     = a5.get("message", "")           if isinstance(a5, dict) else ""

        cache_entry = cache_data.get(company_name, {})
        meta = cache_entry.get("meta", {})
        industry = meta.get("industry", "Unknown")
        size     = meta.get("size", "MID")
        region   = meta.get("region", "Unknown")
        employees = meta.get("employees", 500)

        descriptor = f"{industry} · {employees} employees · {size} · {region}"
        receptivity_map = {"HIGH": "HIGH — ACT WITHIN 90 DAYS", "MEDIUM": "MODERATE — ACT WITHIN 6 MONTHS", "LOW": "LOW — MONITOR"}

        new_data = {
            "descriptor":  descriptor,
            "receptivity": receptivity_map.get(priority, "LOW — MONITOR"),
            "pain_level":  paint_level,
            "pain_tags":   [paint_level + " PAIN"],
            "competitor":  False,
            "agent1": {"company_name": company_name, "domain": domain, "industry": industry, "size": size, "estimated_employees": employees, "region": region},
            "agent2": {"fit_type": "TARGET", "company_state": "SCALE_UP", "expansion_score": a2.get("expansion_score", 0) if isinstance(a2, dict) else 0, "strain_score": a2.get("strain_score", 0) if isinstance(a2, dict) else 0, "risk_score": a2.get("risk_score", 0) if isinstance(a2, dict) else 0, "pain_score": a2.get("pain_score", 0) if isinstance(a2, dict) else 0, "pain_level": paint_level, "signals": a2.get("signals", []) if isinstance(a2, dict) else []},
            "agent3": {"priority": priority, "opportunity_score": opp_score, "intent_score": intent, "conversion_score": conv, "deal_size_score": deal_sz, "expansion_score": expansion, "strain_score": a2.get("strain_score", 0) if isinstance(a2, dict) else 0, "risk_score": a3.get("risk_score", 0) if isinstance(a3, dict) else 0, "key_signals": key_signals, "summary": a3.get("summary", "") if isinstance(a3, dict) else "", "llm_reasoning": a3.get("llm_reasoning", "") if isinstance(a3, dict) else ""},
            "agent35": {"buying_style": strategy, "tech_strength": meta.get("internal_tech_strength", 0.5), "offer": offer, "entry_point": entry_pt, "strategy_note": f"{company_name} → {strategy}"},
            "agent4": {"priority": priority, "strategy": strategy, "recommended_offer": offer, "entry_point": entry_pt, "intent_score": intent, "conversion_score": conv, "deal_size_score": deal_sz, "risk_score": 0.05, "key_signals": key_signals},
            "agent5": {"persona": persona, "channel": channel, "subject": subject, "message": message, "priority": priority, "conversion_score": conv, "deal_size_score": deal_sz},
            "agent6": a6 if isinstance(a6, dict) else {},
            "financials": {"quarters": [], "margin": [], "revenue": []}, "hiring": [],
            "scoreBreakdown": [{"label": "Intent", "value": int(intent * 35), "max": 35}, {"label": "Conversion", "value": int(conv * 25), "max": 25}, {"label": "Deal Size", "value": int(deal_sz * 20), "max": 20}, {"label": "Signal Depth", "value": int(expansion * 20), "max": 20}],
            "timeline": [], "painClusters": [],
            "decisionMaker": {"name": "", "role": persona, "messaging": {"angle": offer, "vocab": key_signals, "tone": strategy.lower()}},
            "outreach": {"email": message, "linkedin": message, "opener": subject, "footnote": f"Channel: {channel}"},
            "capabilityMatch": [], "strongestMatch": {},
            "trace": [
                {"time": "00:01", "agent": "DATA_COLLECTION", "action": f"Sources: search_cache.json + Google News RSS for '{company_name}'"},
                {"time": "00:05", "agent": "SIGNAL_EXTRACTION", "action": f"Pain: {paint_level} | Key signals: {', '.join(key_signals)}"},
                {"time": "00:10", "agent": "OPPORTUNITY_SCORING", "action": f"Score: {score_int_val}/100, Priority: {priority}"},
                {"time": "00:14", "agent": "DECISION_MAKER", "action": f"Strategy: {strategy} → {offer}"},
                {"time": "00:18", "agent": "RECOMMENDER", "action": f"Lead service: {a6.get('lead_service', '?') if isinstance(a6, dict) else '?'}"},
                {"time": "00:24", "agent": "OUTREACH", "action": f"Persona: {persona} · Channel: {channel}"},
            ],
        }

        from sqlalchemy.orm.attributes import flag_modified
        existing = db.query(CompanyRecord).filter(CompanyRecord.id == slug).first()
        if existing:
            existing.score = score_int_val; existing.confidence = confidence
            existing.coverage = int(expansion * 100); existing.descriptor = descriptor
            existing.data = new_data; existing.updated_at = utcnow()
            flag_modified(existing, "data")
        else:
            db.add(CompanyRecord(id=slug, scan_id=scan_id, name=company_name, descriptor=descriptor,
                                  score=score_int_val, confidence=confidence, coverage=int(expansion * 100),
                                  data=new_data, created_at=utcnow(), updated_at=utcnow()))
        db.commit()

        scan.company_name = f"DONE:{slug}"
        scan.status       = "completed"
        scan.progress     = 1.0
        scan.completed_at = utcnow()
        db.commit()
        logger.info(f"Search-discover complete: {company_name} (slug={slug}, score={score_int_val})")

    except Exception as e:
        logger.error(f"Search-discover pipeline error: {e}", exc_info=True)
        try:
            scan = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
            if scan:
                scan.status = "failed"; scan.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
        _active_scan_id = None
        _scan_lock.release()



# ── Pipeline runner ──────────────────────────────────────────

def _run_discovery_pipeline(scan_id: str):
    """Run the 5-agent pipeline in a background thread. Calls each agent directly."""
    global _active_scan_id

    db = SessionLocal()
    try:
        scan = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
        if not scan:
            return

        scan.status = "running"
        scan.progress = 0.05
        scan.agents_pending = ["DISCOVERY", "SIGNALS", "SCORING", "STRATEGY", "DECISION", "OUTREACH"]
        db.commit()

        # ── Fresh import of pipeline modules ──────────────────
        for mod in list(sys.modules.keys()):
            if mod.startswith(("agent", "config", "models", "orchestrator", "demo_data", "scraper")):
                del sys.modules[mod]

        import agent1_discovery
        import agent2_signals
        import agent3_scoring
        import agent35_strategy
        import agent4_decision_maker
        import agent5_outreach

        # ── Agent 1: Target Discovery ─────────────────────────
        scan.company_name = "Discovering targets..."
        scan.progress = 0.10
        scan.agents_completed = ["DISCOVERY_INIT"]
        db.commit()

        query = "AI analytics, data platform, and ML database companies looking for data engineering and cloud modernization"
        candidates = agent1_discovery.run(query)

        scan.progress = 0.25
        scan.agents_completed = ["DISCOVERY"]
        scan.agents_pending = ["SIGNALS", "SCORING", "STRATEGY", "DECISION", "OUTREACH"]
        db.commit()

        if not candidates:
            scan.status = "failed"
            scan.error_message = "Agent 1 returned no candidates."
            db.commit()
            return

        # ── Agent 2: Signal Extraction ────────────────────────
        signals = agent2_signals.run(candidates)
        signal_map = {s["company_name"]: s for s in signals}

        scan.progress = 0.40
        scan.agents_completed = ["DISCOVERY", "SIGNALS"]
        scan.agents_pending = ["SCORING", "STRATEGY", "DECISION", "OUTREACH"]
        db.commit()

        # ── Agent 3: Opportunity Scoring ──────────────────────
        scored = agent3_scoring.run(candidates, signals)
        scored_map = {s["company_name"]: s for s in scored}

        scan.progress = 0.55
        scan.agents_completed = ["DISCOVERY", "SIGNALS", "SCORING"]
        scan.agents_pending = ["STRATEGY", "DECISION", "OUTREACH"]
        db.commit()

        # ── Agent 3.5: Strategy ───────────────────────────────
        strategies = agent35_strategy.run(scored, signals)
        strategy_map = {s["company_name"]: s for s in strategies}

        scan.progress = 0.65
        scan.agents_completed = ["DISCOVERY", "SIGNALS", "SCORING", "STRATEGY"]
        scan.agents_pending = ["DECISION", "OUTREACH"]
        db.commit()

        # ── Agent 4: Decision Maker ───────────────────────────
        decisions = agent4_decision_maker.run(scored)
        decision_map = {d["company_name"]: d for d in decisions}

        scan.progress = 0.80
        scan.agents_completed = ["DISCOVERY", "SIGNALS", "SCORING", "STRATEGY", "DECISION"]
        scan.agents_pending = ["OUTREACH"]
        db.commit()

        # ── Agent 5: Outreach ─────────────────────────────────
        outreach_list = agent5_outreach.run(decisions)
        outreach_map = {o["company_name"]: o for o in outreach_list}

        scan.progress = 0.90
        scan.agents_completed = ["DISCOVERY", "SIGNALS", "SCORING", "STRATEGY", "DECISION", "OUTREACH"]
        scan.agents_pending = []
        db.commit()

        # ── Assemble and save each company ────────────────────
        for candidate in candidates:
            name = candidate.company_name
            slug = name.lower().replace(" ", "-").replace(".", "")

            a1 = {
                "company_name": name,
                "domain": candidate.domain,
                "industry": candidate.industry,
                "size": candidate.size,
                "estimated_employees": candidate.estimated_employees,
                "region": candidate.region,
            }

            a2 = signal_map.get(name, {})
            a3 = scored_map.get(name, {})
            a35 = strategy_map.get(name, {})
            a4 = decision_map.get(name, {})
            a5 = outreach_map.get(name, {})

            # Scores for top-level indexed columns
            opp_score = a3.get("opportunity_score", 0.5)
            priority = a3.get("priority", "LOW")
            score_int = _score_int(opp_score)
            confidence = _priority_to_confidence(priority)

            # Pain level from agent2
            pain_level = a2.get("pain_level", "LOW")

            # Receptivity string from priority
            receptivity_map = {
                "HIGH":   "HIGH — ACT WITHIN 90 DAYS",
                "MEDIUM": "MODERATE — ACT WITHIN 6 MONTHS",
                "LOW":    "LOW — MONITOR",
            }
            receptivity = receptivity_map.get(priority, "LOW — MONITOR")

            # Descriptor string
            descriptor = f"{a1['industry']} · {a1['estimated_employees']} employees · {a1['size']} · {a1['region']}"

            # Signal confidence for coverage
            sig_confidence = a3.get("opportunity_score", 0.5)

            # Build flat data blob — all agents namespaced
            data = {
                "descriptor": descriptor,
                "receptivity": receptivity,
                "pain_level": pain_level,
                "pain_tags": [pain_level + " PAIN"],

                "agent1": a1,
                "agent2": {
                    "fit_type":        a2.get("fit_type", "TARGET"),
                    "company_state":   a2.get("company_state", "UNKNOWN"),
                    "expansion_score": a2.get("expansion_score", 0.0),
                    "strain_score":    a2.get("strain_score", 0.0),
                    "risk_score":      a2.get("risk_score", 0.0),
                    "pain_score":      a2.get("pain_score", 0.0),
                    "pain_level":      pain_level,
                    "signals":         a2.get("signals", []),
                },
                "agent3": {
                    "priority":         priority,
                    "opportunity_score": opp_score,
                    "intent_score":     a3.get("intent_score", 0.0),
                    "conversion_score": a3.get("conversion_score", 0.0),
                    "deal_size_score":  a3.get("deal_size_score", 0.0),
                    "expansion_score":  a3.get("expansion_score", 0.0),
                    "strain_score":     a3.get("strain_score", 0.0),
                    "risk_score":       a3.get("risk_score", 0.0),
                    "key_signals":      a3.get("key_signals", []),
                    "summary":          a3.get("summary", ""),
                },
                "agent35": {
                    "buying_style":   a35.get("buying_style", ""),
                    "tech_strength":  a35.get("tech_strength", 0.0),
                    "offer":          a35.get("offer", ""),
                    "entry_point":    a35.get("entry_point", ""),
                    "strategy_note":  a35.get("strategy_note", ""),
                },
                "agent4": {
                    "priority":          a4.get("priority", "LOW"),
                    "strategy":          a4.get("strategy", "MONITOR"),
                    "recommended_offer": a4.get("recommended_offer", ""),
                    "entry_point":       a4.get("entry_point", ""),
                    "intent_score":      a4.get("intent_score", 0.0),
                    "conversion_score":  a4.get("conversion_score", 0.0),
                    "deal_size_score":   a4.get("deal_size_score", 0.0),
                    "risk_score":        a4.get("risk_score", 0.0),
                    "key_signals":       a4.get("key_signals", []),
                },
                "agent5": {
                    "persona":           a5.get("persona", ""),
                    "channel":           a5.get("channel", ""),
                    "subject":           a5.get("subject", ""),
                    "message":           a5.get("message", ""),
                    "priority":          a5.get("priority", "LOW"),
                    "conversion_score":  a5.get("conversion_score", 0.0),
                    "deal_size_score":   a5.get("deal_size_score", 0.0),
                },

                # Legacy fields kept so existing frontend code doesn't break
                "financials":     {"quarters": [], "margin": [], "revenue": []},
                "hiring":         [],
                "scoreBreakdown": [
                    {"label": "Intent",       "value": int(a3.get("intent_score", 0) * 35),     "max": 35},
                    {"label": "Conversion",   "value": int(a3.get("conversion_score", 0) * 25), "max": 25},
                    {"label": "Deal Size",    "value": int(a3.get("deal_size_score", 0) * 20),  "max": 20},
                    {"label": "Signal Depth", "value": int(a2.get("expansion_score", 0) * 20),  "max": 20},
                ],
                "timeline": [],
                "painClusters": [],
                "decisionMaker": {
                    "name": a4.get("strategy", ""),
                    "role": a5.get("persona", ""),
                    "messaging": {
                        "angle": a4.get("recommended_offer", ""),
                        "vocab": a4.get("key_signals", []),
                        "tone":  a4.get("strategy", "consultative"),
                    }
                },
                "outreach": {
                    "email":    a5.get("message", ""),
                    "linkedin": a5.get("message", ""),
                    "opener":   a5.get("subject", ""),
                    "footnote": f"Channel: {a5.get('channel', '')} · Strategy: {a4.get('strategy', '')}",
                },
                "capabilityMatch": [],
                "strongestMatch":  {},
                "trace": [
                    {"time": "00:01", "agent": "TARGET_DISCOVERY",   "action": f"Found {name} — {a1['industry']}, {a1['size']}, {a1['region']}"},
                    {"time": "00:05", "agent": "SIGNAL_EXTRACTION",  "action": f"Pain: {pain_level} (expansion={a2.get('expansion_score', 0):.2f}, strain={a2.get('strain_score', 0):.2f}, risk={a2.get('risk_score', 0):.2f})"},
                    {"time": "00:10", "agent": "OPPORTUNITY_SCORING", "action": f"Score: {score_int}/100, Priority: {priority}, Intent: {a3.get('intent_score', 0):.2f}, Conversion: {a3.get('conversion_score', 0):.2f}"},
                    {"time": "00:14", "agent": "STRATEGY",           "action": f"Style: {a35.get('buying_style', '')} — {a35.get('offer', '')}"},
                    {"time": "00:18", "agent": "DECISION_MAKER",     "action": f"Strategy: {a4.get('strategy', '')} → {a4.get('recommended_offer', '')} via {a4.get('entry_point', '')}"},
                    {"time": "00:24", "agent": "OUTREACH",           "action": f"Persona: {a5.get('persona', '')} · Channel: {a5.get('channel', '')} · Subject: {a5.get('subject', '')}"},
                ],
            }

            # Upsert company record
            existing = db.query(CompanyRecord).filter(CompanyRecord.id == slug).first()
            if existing:
                existing.score      = score_int
                existing.confidence = confidence
                existing.coverage   = int(sig_confidence * 100)
                existing.descriptor = descriptor
                existing.data       = data
                existing.updated_at = utcnow()
            else:
                db.add(CompanyRecord(
                    id          = slug,
                    scan_id     = scan_id,
                    name        = name,
                    descriptor  = descriptor,
                    score       = score_int,
                    confidence  = confidence,
                    coverage    = int(sig_confidence * 100),
                    data        = data,
                    created_at  = utcnow(),
                    updated_at  = utcnow(),
                ))
            db.commit()
            logger.info(f"Saved company: {name} (score={score_int}, priority={priority})")

        # ── Mark complete ─────────────────────────────────────
        scan.status       = "completed"
        scan.progress     = 1.0
        scan.completed_at = utcnow()
        db.commit()
        logger.info(f"Discovery scan {scan_id} completed — {len(candidates)} companies saved")

    except Exception as e:
        logger.error(f"Discovery pipeline error: {e}", exc_info=True)
        try:
            scan = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
            if scan:
                scan.status        = "failed"
                scan.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
        _active_scan_id = None
        _scan_lock.release()


# ── Routes ────────────────────────────────────────────────────

from pydantic import BaseModel

class SearchDiscoverRequest(BaseModel):
    company_name: str
    domain: str | None = None


@router.post("/companies/search-discover")
def search_discover(req: SearchDiscoverRequest, db: Session = Depends(get_db)):
    """
    Scrape and analyse a user-specified company by name.
    Runs the full scraper + 6-agent pipeline in background.
    Returns scan_id for polling. Status 'completed' means slug ready in company_name field.
    """
    global _active_scan_id

    if not _scan_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail=f"A scan is already running ({_active_scan_id}). Wait for it to finish.",
        )

    company_name = req.company_name.strip()
    domain = req.domain or _guess_domain(company_name)

    scan_id = new_uuid()
    _active_scan_id = scan_id

    scan = ScanRecord(
        id           = scan_id,
        user_request = f"Search-discover: {company_name}",
        status       = "queued",
        progress     = 0.0,
        created_at   = utcnow(),
    )
    db.add(scan)
    db.commit()

    threading.Thread(
        target=_run_search_discover_pipeline,
        args=(company_name, domain, scan_id),
        daemon=True,
    ).start()

    logger.info(f"Search-discover queued: {company_name} @ {domain} — scan_id={scan_id}")
    return {
        "scan_id":  scan_id,
        "status":   "queued",
        "company":  company_name,
        "domain":   domain,
        "message":  "Scraping and analysing...",
    }


@router.post("/discover")

def trigger_discovery(db: Session = Depends(get_db)):
    """
    Auto-discover target companies using the 5-agent pipeline.
    Only one scan runs at a time.
    """
    global _active_scan_id

    if not _scan_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail=f"A scan is already running (ID: {_active_scan_id}). Wait for it to finish."
        )

    scan_id        = new_uuid()
    _active_scan_id = scan_id

    scan = ScanRecord(
        id           = scan_id,
        user_request = "Auto-discover target companies",
        status       = "queued",
        progress     = 0.0,
        created_at   = utcnow(),
    )
    db.add(scan)
    db.commit()

    threading.Thread(
        target=_run_discovery_pipeline,
        args=(scan_id,),
        daemon=True,
    ).start()

    logger.info(f"Discovery scan {scan_id} queued")
    return {
        "scan_id":                    scan_id,
        "status":                     "queued",
        "estimated_duration_seconds": 30,
        "message":                    "5-agent pipeline starting...",
    }


@router.get("/discover/{scan_id}")
def get_discovery_status(scan_id: str, db: Session = Depends(get_db)):
    """Check discovery scan progress."""
    scan = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return {
        "scan_id":          scan.id,
        "status":           scan.status,
        "progress":         scan.progress or 0.0,
        "company_name":     scan.company_name,
        "agents_completed": scan.agents_completed or [],
        "agents_pending":   scan.agents_pending   or [],
        "error_message":    scan.error_message,
    }
