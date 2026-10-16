"""
DataVex Agent Diagnostic — Run each agent individually, capture raw output.
This script tests each of the 5 pipeline agents step-by-step.
"""
import sys, os, json, time

# Add pipeline to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "datavex_pipeline"))

# Load env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

# Force env vars for Ollama
os.environ["LLM_MODEL"] = os.getenv("BYTEZ_MODEL", "llama3.1:8b")
os.environ["OPENAI_API_KEY"] = os.getenv("BYTEZ_API_KEY", "ollama")
os.environ["BYTEZ_API_KEY"] = os.getenv("BYTEZ_API_KEY", "ollama")
os.environ["BYTEZ_BASE_URL"] = os.getenv("BYTEZ_BASE_URL", "http://100.109.131.90:11434/v1")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "agent_diagnostic.txt")

def log(msg):
    """Print and write to file."""
    print(msg)
    with open(OUTPUT_FILE, "a") as f:
        f.write(msg + "\n")

def dump_obj(label, obj, indent=2):
    """Dump a Pydantic model or dict to readable text."""
    if hasattr(obj, "model_dump"):
        data = obj.model_dump()
    elif hasattr(obj, "__dict__"):
        data = obj.__dict__
    else:
        data = obj
    text = json.dumps(data, indent=indent, default=str, ensure_ascii=False)
    log(f"\n{'─'*60}")
    log(f"  {label}")
    log(f"{'─'*60}")
    log(text)

# ── Clear output file ──
with open(OUTPUT_FILE, "w") as f:
    f.write("=" * 70 + "\n")
    f.write("  DATAVEX AGENT DIAGNOSTIC\n")
    f.write(f"  Model: {os.environ.get('LLM_MODEL', 'unknown')}\n")
    f.write(f"  Base URL: {os.environ.get('BYTEZ_BASE_URL', 'unknown')}\n")
    f.write(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 70 + "\n\n")

# ── Check config ──
log("\n[STEP 0] Checking LLM config...")
from config import OFFLINE_MODE, LLM_MODEL, OPENAI_BASE_URL, client
log(f"  OFFLINE_MODE = {OFFLINE_MODE}")
log(f"  LLM_MODEL    = {LLM_MODEL}")
log(f"  BASE_URL     = {OPENAI_BASE_URL}")
log(f"  Client       = {'CONNECTED' if client else 'NONE (offline)'}")

if OFFLINE_MODE:
    log("\n  ⚠ OFFLINE MODE — agents will use hardcoded fallbacks, NOT the LLM")
    log("  This means all data is pre-generated demo data, not real LLM output.")
else:
    log("\n  ✓ ONLINE MODE — agents will call Ollama LLM for real analysis")

# Test LLM with a simple call
if client:
    log("\n[STEP 0.5] Testing LLM connection with a simple prompt...")
    try:
        t0 = time.time()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "Say 'hello datavex' and nothing else."}],
            temperature=0.1,
            max_tokens=20,
        )
        answer = resp.choices[0].message.content.strip()
        log(f"  ✓ LLM responded in {time.time()-t0:.1f}s: '{answer}'")
    except Exception as e:
        log(f"  ✗ LLM connection FAILED: {e}")

# ════════════════════════════════════════════════════════════
# AGENT 1 — Target Discovery
# ════════════════════════════════════════════════════════════
log("\n\n" + "=" * 70)
log("  AGENT 1 — TARGET DISCOVERY")
log("=" * 70)

from models import UserIntent, DealProfile
import agent1_discovery

intent = UserIntent(raw_text="AI analytics, data platform, and ML database companies looking for data engineering and cloud modernization")
profile = DealProfile()

log(f"\n  Input: {intent.raw_text}")
log(f"  Deal: min=${profile.min_deal_usd:,}, max=${profile.max_deal_usd:,}, regions={profile.target_regions}, sizes={profile.preferred_company_sizes}")

t1 = time.time()
try:
    candidates = agent1_discovery.run(intent, profile)
    log(f"\n  ✓ Agent 1 completed in {time.time()-t1:.1f}s — found {len(candidates)} candidates")
    
    for i, c in enumerate(candidates):
        dump_obj(f"Candidate {i+1}: {c.company_name}", c)
        log(f"\n  Summary: {c.company_name} | {c.industry} | {c.size} | {c.estimated_employees} emp | {c.region}")
        log(f"           cap_score={c.capability_score:.3f} | size_fit={c.size_fit:.1f} | geo_fit={c.geo_fit:.1f} | ind_fit={c.industry_fit:.1f}")
        log(f"           TOTAL MATCH SCORE = {c.initial_match_score:.3f}")
        
        # Verdict
        if c.initial_match_score >= 0.6:
            log(f"           VERDICT: ✓ STRONG MATCH")
        elif c.initial_match_score >= 0.4:
            log(f"           VERDICT: ~ MODERATE MATCH")
        else:
            log(f"           VERDICT: ✗ WEAK MATCH (below 0.4 threshold)")
except Exception as e:
    log(f"\n  ✗ AGENT 1 FAILED: {e}")
    import traceback
    log(traceback.format_exc())
    candidates = []

# ════════════════════════════════════════════════════════════
# AGENT 2 — Signal Extraction
# ════════════════════════════════════════════════════════════
log("\n\n" + "=" * 70)
log("  AGENT 2 — SIGNAL EXTRACTION")
log("=" * 70)

if not candidates:
    log("  ⚠ Skipping — no candidates from Agent 1")
    all_signals = []
else:
    import agent2_signals
    
    t2 = time.time()
    try:
        all_signals = agent2_signals.run(candidates)
        log(f"\n  ✓ Agent 2 completed in {time.time()-t2:.1f}s — signals for {len(all_signals)} companies")
        
        for i, sig in enumerate(all_signals):
            dump_obj(f"Signals for: {sig.company_name}", sig)
            
            log(f"\n  Company: {sig.company_name}")
            log(f"  State:   {sig.company_state}")
            
            # Check each signal
            for signal_name, signal_obj in [("PIVOT", sig.pivot), ("TECH_DEBT", sig.tech_debt), ("FISCAL_PRESSURE", sig.fiscal_pressure)]:
                if signal_obj:
                    log(f"  {signal_name}: DETECTED (confidence={signal_obj.confidence:.2f}, label='{signal_obj.label}')")
                    for e in signal_obj.evidence:
                        log(f"    └─ [{e.source}] {e.text[:120]}...")
                    
                    # Check if evidence looks real or hallucinated
                    if signal_obj.evidence:
                        log(f"    ⚠ Evidence check: {len(signal_obj.evidence)} items — check if these are from real data or LLM hallucination")
                else:
                    log(f"  {signal_name}: NOT DETECTED")
            
            if sig.why_now_triggers:
                log(f"  WHY NOW TRIGGERS: {len(sig.why_now_triggers)} items")
                for t_item in sig.why_now_triggers:
                    log(f"    └─ {json.dumps(t_item, default=str)}")
            
            if sig.raw_texts:
                log(f"  RAW TEXTS: {len(sig.raw_texts)} source documents fed to LLM")
                for rt in sig.raw_texts[:3]:
                    text_preview = str(rt.get("text", ""))[:100]
                    log(f"    └─ [{rt.get('source', '?')}] {text_preview}...")
            else:
                log(f"  RAW TEXTS: NONE — ⚠ this means signals are from demo_data, not live scraping")
    except Exception as e:
        log(f"\n  ✗ AGENT 2 FAILED: {e}")
        import traceback
        log(traceback.format_exc())
        all_signals = []

# ════════════════════════════════════════════════════════════
# AGENT 3 — Opportunity Scoring
# ════════════════════════════════════════════════════════════
log("\n\n" + "=" * 70)
log("  AGENT 3 — OPPORTUNITY SCORING")
log("=" * 70)

if not candidates or not all_signals:
    log("  ⚠ Skipping — missing data from previous agents")
    opportunities = []
else:
    import agent3_scoring
    
    t3 = time.time()
    try:
        opportunities = agent3_scoring.run(candidates, all_signals)
        log(f"\n  ✓ Agent 3 completed in {time.time()-t3:.1f}s — scored {len(opportunities)} companies")
        
        for i, opp in enumerate(opportunities):
            dump_obj(f"Scoring for: {opp.company_name}", opp)
            
            log(f"\n  Company: {opp.company_name}")
            log(f"  Score:   {opp.opportunity_score:.3f} (= {int(opp.opportunity_score * 100)}/100)")
            log(f"  Priority: {opp.priority}")
            log(f"  Window:   {opp.timing_window}")
            log(f"  Cap Alignment: {opp.capability_alignment:.2f}")
            log(f"  Urgency:       {opp.urgency_score:.2f}")
            log(f"  Confidence:    {opp.confidence:.2f}")
            
            if opp.why_we_win:
                log(f"  WHY WE WIN:")
                for w in opp.why_we_win:
                    log(f"    └─ {w}")
            
            if opp.risks:
                log(f"  RISKS:")
                for r in opp.risks:
                    log(f"    └─ {r}")
            
            if opp.strategic_summary:
                log(f"  SUMMARY: {opp.strategic_summary[:200]}")
    except Exception as e:
        log(f"\n  ✗ AGENT 3 FAILED: {e}")
        import traceback
        log(traceback.format_exc())
        opportunities = []

# ════════════════════════════════════════════════════════════
# AGENT 4 — Decision Maker
# ════════════════════════════════════════════════════════════
log("\n\n" + "=" * 70)
log("  AGENT 4 — DECISION MAKER")
log("=" * 70)

if not opportunities or not all_signals:
    log("  ⚠ Skipping — missing data from previous agents")
    decision_makers = []
else:
    import agent4_decision_maker
    
    t4 = time.time()
    try:
        decision_makers = agent4_decision_maker.run(opportunities, all_signals)
        log(f"\n  ✓ Agent 4 completed in {time.time()-t4:.1f}s — DMs for {len(decision_makers)} companies")
        
        for i, dm_out in enumerate(decision_makers):
            dump_obj(f"Decision Maker for: {dm_out.company_name}", dm_out)
            
            dm = dm_out.decision_maker
            log(f"\n  Company: {dm_out.company_name}")
            log(f"  DM Name: {dm.name}")
            log(f"  DM Role: {dm.role}")
            log(f"  ⚠ IS THE NAME REAL? Check: '{dm.name}' — if this is a specific person's name,")
            log(f"    it's likely hallucinated by the LLM (no LinkedIn scraping)")
            log(f"  Priority: focus={dm.priority_profile.primary_focus}, style={dm.priority_profile.communication_style}")
            log(f"  Messaging Angle: {dm.messaging_angle[:150]}")
            
            if dm.pain_points_aligned:
                log(f"  Pain Points:")
                for p in dm.pain_points_aligned:
                    log(f"    └─ {p}")
    except Exception as e:
        log(f"\n  ✗ AGENT 4 FAILED: {e}")
        import traceback
        log(traceback.format_exc())
        decision_makers = []

# ════════════════════════════════════════════════════════════
# AGENT 5 — Outreach Generation
# ════════════════════════════════════════════════════════════
log("\n\n" + "=" * 70)
log("  AGENT 5 — OUTREACH GENERATION")
log("=" * 70)

if not opportunities or not all_signals or not decision_makers:
    log("  ⚠ Skipping — missing data from previous agents")
else:
    import agent5_outreach
    
    t5 = time.time()
    try:
        outreach_kits = agent5_outreach.run(opportunities, all_signals, decision_makers)
        log(f"\n  ✓ Agent 5 completed in {time.time()-t5:.1f}s — outreach for {len(outreach_kits)} companies")
        
        for i, out in enumerate(outreach_kits):
            dump_obj(f"Outreach for: {out.company_name}", out)
            
            log(f"\n  Company: {out.company_name}")
            log(f"  DM: {out.decision_maker_name} ({out.decision_maker_role})")
            log(f"  Tone: {out.tone}")
            log(f"  Confidence: {out.confidence:.2f}")
            
            log(f"\n  ── EMAIL ──")
            log(out.email[:500] if out.email else "  (empty)")
            
            log(f"\n  ── LINKEDIN DM ──")
            log(out.linkedin_dm[:300] if out.linkedin_dm else "  (empty)")
            
            log(f"\n  ── CALL OPENER ──")
            log(out.call_opener[:300] if out.call_opener else "  (empty)")
    except Exception as e:
        log(f"\n  ✗ AGENT 5 FAILED: {e}")
        import traceback
        log(traceback.format_exc())

# ════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════
log("\n\n" + "=" * 70)
log("  DIAGNOSTIC SUMMARY")
log("=" * 70)
log(f"  Mode: {'OFFLINE (demo data)' if OFFLINE_MODE else 'ONLINE (Ollama LLM)'}")
log(f"  Model: {LLM_MODEL}")
log(f"  Agent 1 (Discovery):   {'✓' if candidates else '✗'} — {len(candidates)} candidates")
log(f"  Agent 2 (Signals):     {'✓' if all_signals else '✗'} — {len(all_signals)} signal sets")
log(f"  Agent 3 (Scoring):     {'✓' if opportunities else '✗'} — {len(opportunities)} scores")
log(f"  Agent 4 (DM):          {'✓' if decision_makers else '✗'} — {len(decision_makers)} profiles")
log(f"  Agent 5 (Outreach):    {'✓' if 'outreach_kits' in dir() and outreach_kits else '✗'}")
log(f"\n  Full output saved to: {OUTPUT_FILE}")
log(f"  Total time: check timestamps above")
print(f"\n  ✓ Done! Results saved to: {OUTPUT_FILE}")
