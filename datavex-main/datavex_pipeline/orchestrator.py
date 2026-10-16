"""
DataVex Pipeline — Orchestrator (standalone CLI path)
Runs the full agent pipeline sequentially with progress tracking.

NOTE: This calls the SAME agent modules, with the SAME call signatures,
that backend/app/routers/discover.py uses for the live API. Agents return
plain dicts (not Pydantic models) except CandidateCompany from Agent 1 —
keep this file in sync with discover.py's calling convention if either
changes.
"""
import logging
import time
from datetime import datetime

from models import UserIntent, DealProfile

import agent1_discovery
import agent2_signals
import agent3_scoring
import agent35_strategy
import agent4_decision_maker
import agent5_outreach
import agent6_recommender

logger = logging.getLogger("datavex_pipeline")

# ── Live Tracker ────────────────────────────────────────────
TRACKER_PATH = "tracker.md"


def _update_tracker(stage: str, details: str):
    """Append progress to tracker.md for live pickup."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"| {ts} | {stage} | {details} |\n"
    try:
        with open(TRACKER_PATH, "a") as f:
            f.write(line)
    except Exception:
        pass


def _init_tracker(user_input: str):
    """Initialize the tracker file."""
    with open(TRACKER_PATH, "w") as f:
        f.write("# DataVex Pipeline — Live Tracker\n\n")
        f.write(f"**Query:** {user_input}\n")
        f.write(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Time | Stage | Details |\n")
        f.write("|------|-------|---------|\n")


# ── Pipeline ────────────────────────────────────────────────

def run_pipeline(user_input: str, deal_profile: dict | None = None) -> list[dict]:
    """
    Run the full agent pipeline.

    Args:
        user_input: Natural language query, e.g. "mid-size fintech SaaS
                    companies doing AI in India"
        deal_profile: Optional dict with min_deal_usd, max_deal_usd,
                      target_regions, preferred_company_sizes

    Returns:
        List of dicts, one per qualifying company, each shaped as:
        {
            "company_name": str,
            "candidate": dict,       # Agent 1 output
            "signals": dict,         # Agent 2 output
            "opportunity": dict,     # Agent 3 output
            "strategy": dict,        # Agent 3.5 output
            "decision": dict,        # Agent 4 output
            "recommendation": dict,  # Agent 6 output
            "outreach": dict,        # Agent 5 output
        }
    """
    start = time.time()

    # Parse/validate inputs (also used for CLI echo + tracker)
    UserIntent(raw_text=user_input)
    profile = DealProfile(**(deal_profile or {}))

    _init_tracker(user_input)
    _update_tracker("INIT", f"Intent: {user_input[:80]}")

    # ── Agent 1: Target Discovery ───────────────────────────
    print("\n" + "=" * 60)
    print("  Agent 1 — Target Discovery")
    print("=" * 60)
    t1 = time.time()
    candidates = agent1_discovery.run(user_input, profile.model_dump())
    names = ", ".join(c.company_name for c in candidates)
    _update_tracker("AGENT 1 ✓", f"{len(candidates)} candidates: {names} ({time.time() - t1:.1f}s)")

    if not candidates:
        print("  ⚠ No candidates found above threshold. Exiting.")
        _update_tracker("EXIT", "No candidates above threshold")
        return []

    for c in candidates:
        print(f"  ✓ {c.company_name:20s} match={c.initial_match_score:.3f}  cap={c.capability_score:.2f}  size={c.size_fit:.1f}  geo={c.geo_fit:.1f}")

    # ── Agent 2: Signal Extraction ──────────────────────────
    print("\n" + "=" * 60)
    print("  Agent 2 — Signal Extraction")
    print("=" * 60)
    t2 = time.time()
    all_signals = agent2_signals.run(candidates)
    _update_tracker("AGENT 2 ✓", f"Signals extracted for {len(all_signals)} companies ({time.time() - t2:.1f}s)")

    for s in all_signals:
        print(f"  ✓ {s['company_name']:20s} fit={s['fit_type']:10s} pain={s['pain_level']:6s} score={s['pain_score']:.2f}")

    # ── Agent 3: Opportunity Scoring ────────────────────────
    print("\n" + "=" * 60)
    print("  Agent 3 — Opportunity Scoring")
    print("=" * 60)
    t3 = time.time()
    opportunities = agent3_scoring.run(candidates, all_signals)
    scored_str = ", ".join(f"{o['company_name']}={o['priority']}" for o in opportunities)
    _update_tracker("AGENT 3 ✓", f"Scored: {scored_str} ({time.time() - t3:.1f}s)")

    for o in opportunities:
        print(f"  ✓ {o['company_name']:20s} score={o['opportunity_score']:.3f}  priority={o['priority']:6s}")

    if not opportunities:
        print("  ⚠ All candidates filtered out (e.g. classified as competitors). Exiting.")
        _update_tracker("EXIT", "No opportunities after scoring/competitor filter")
        return []

    # ── Agent 3.5: Sales Strategy ───────────────────────────
    print("\n" + "=" * 60)
    print("  Agent 3.5 — Sales Strategy")
    print("=" * 60)
    t35 = time.time()
    strategies = agent35_strategy.run(opportunities, all_signals)
    _update_tracker("AGENT 3.5 ✓", f"Strategies assigned for {len(strategies)} companies ({time.time() - t35:.1f}s)")

    # ── Agent 4: GTM Decision ───────────────────────────────
    print("\n" + "=" * 60)
    print("  Agent 4 — GTM Decision")
    print("=" * 60)
    t4 = time.time()
    decisions = agent4_decision_maker.run(opportunities)
    dec_str = ", ".join(f"{d['company_name']}={d['strategy']}" for d in decisions)
    _update_tracker("AGENT 4 ✓", f"Decisions: {dec_str} ({time.time() - t4:.1f}s)")

    for d in decisions:
        print(f"  ✓ {d['company_name']:20s} strategy={d['strategy']:12s} offer={d['recommended_offer']}")

    # ── Agent 6: What to Sell (RAG Recommender) ─────────────
    print("\n" + "=" * 60)
    print("  Agent 6 — What to Sell (RAG Recommender)")
    print("=" * 60)
    t6 = time.time()
    recommendations = agent6_recommender.run(decisions, all_signals)
    rec_str = ", ".join(f"{r['company_name']}={r.get('lead_service', '?')}" for r in recommendations)
    _update_tracker("AGENT 6 ✓", f"Recommendations: {rec_str} ({time.time() - t6:.1f}s)")

    # ── Agent 5: Outreach Generation ────────────────────────
    print("\n" + "=" * 60)
    print("  Agent 5 — Outreach Generation")
    print("=" * 60)
    t5 = time.time()
    outreach_kits = agent5_outreach.run(decisions, recommendations, all_signals)
    _update_tracker("AGENT 5 ✓", f"Outreach generated for {len(outreach_kits)} targets ({time.time() - t5:.1f}s)")

    for ok in outreach_kits:
        print(f"  ✓ {ok['company_name']:20s} persona={ok['persona']:20s} channel={ok['channel']}")

    # ── Assemble Results ────────────────────────────────────
    sig_map = {s["company_name"]: s for s in all_signals}
    opp_map = {o["company_name"]: o for o in opportunities}
    strat_map = {s["company_name"]: s for s in strategies}
    dec_map = {d["company_name"]: d for d in decisions}
    rec_map = {r["company_name"]: r for r in recommendations}
    out_map = {o["company_name"]: o for o in outreach_kits}

    results = []
    for c in candidates:
        name = c.company_name
        if name not in opp_map:
            # Filtered out during scoring (e.g. competitor) — skip.
            continue
        results.append({
            "company_name": name,
            "candidate": c.model_dump(),
            "signals": sig_map.get(name, {}),
            "opportunity": opp_map.get(name, {}),
            "strategy": strat_map.get(name, {}),
            "decision": dec_map.get(name, {}),
            "recommendation": rec_map.get(name, {}),
            "outreach": out_map.get(name, {}),
        })

    elapsed = time.time() - start
    _update_tracker("DONE", f"Pipeline complete. {len(results)} results. Total: {elapsed:.1f}s")

    print(f"\n{'=' * 60}")
    print(f"  Pipeline complete — {len(results)} results in {elapsed:.1f}s")
    print(f"{'=' * 60}")

    return results


# ── CLI Summary Printer ─────────────────────────────────────

def print_detailed_results(results: list[dict]):
    """Print a structured trace for each company."""
    for r in results:
        opp = r["opportunity"]
        sig = r["signals"]
        dec = r["decision"]
        out = r["outreach"]
        rec = r["recommendation"]

        print(f"\n{'-' * 70}")
        print(f"  {r['company_name']}")
        print(f"  priority={opp.get('priority', '?')}  score={opp.get('opportunity_score', 0):.3f}  pain={sig.get('pain_level', '?')}")
        print(f"{'-' * 70}")

        print("\n  SIGNALS")
        print(f"    expansion={sig.get('expansion_score', 0):.2f}  strain={sig.get('strain_score', 0):.2f}  risk={sig.get('risk_score', 0):.2f}")

        print("\n  OPPORTUNITY")
        print(f"    {opp.get('summary', '')}")
        if opp.get("llm_reasoning"):
            print(f"    Why: {opp['llm_reasoning']}")

        print("\n  STRATEGY / DECISION")
        print(f"    {dec.get('strategy', '')} → {dec.get('recommended_offer', '')} (entry: {dec.get('entry_point', '')})")

        if rec.get("lead_service"):
            print("\n  RECOMMENDATION (what to sell)")
            print(f"    Lead: {rec['lead_service']} — {rec.get('lead_service_reason', '')}")
            if rec.get("upsell_services"):
                print(f"    Upsell: {', '.join(rec['upsell_services'])}")

        print("\n  OUTREACH KIT")
        print(f"    Persona: {out.get('persona', '')}  Channel: {out.get('channel', '')}")
        print(f"    Subject: {out.get('subject', '')}")
        message = out.get("message", "")
        for line in message.split("\n")[:6]:
            print(f"    {line}")
        if len(message.split("\n")) > 6:
            print("    ...")
