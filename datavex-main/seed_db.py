#!/usr/bin/env python3
"""
DataVex — DB Seed Script
Run this once on a fresh device to populate the database from search_cache.json.

Usage:
    cd datavex
    source .venv/bin/activate
    python seed_db.py
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'datavex_pipeline'))

from app.database import SessionLocal, CompanyRecord, Base, engine
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timezone

# Agent 6 — RAG recommender (optional, graceful if unavailable)
try:
    import agent6_recommender
    HAS_AGENT6 = True
except ImportError:
    HAS_AGENT6 = False

def utcnow():
    return datetime.now(timezone.utc)

# ── Create tables if they don't exist ────────────────────────
Base.metadata.create_all(bind=engine)

# ── Load cache ────────────────────────────────────────────────
CACHE_PATH = os.path.join(os.path.dirname(__file__), 'datavex_pipeline', 'search_cache.json')
with open(CACHE_PATH) as f:
    CACHE = json.load(f)

SIGNAL_PATTERNS = {
    'HIRING':  ['hiring', 'open roles', 'expanding team', 'workforce', 'engineer roles', 'data engineer'],
    'FUNDING': ['series', 'raised', 'valuation', 'million', 'billion', 'ipo', 'revenue', 'profit'],
    'INFRA':   ['latency', 'performance', 'pipeline', 'workloads', 'kubernetes', 'spark',
                'microservices', 'infra', 'migration', 'streaming'],
    'PRODUCT': ['launch', 'release', 'new feature', 'platform', 'knowledge graph',
                'digital twin', 'copilot', 'smartfarm', 'ai assistant'],
    'GTM':     ['partnership', 'reseller', 'enterprise agreement', 'customer', 'signed', 'deployed', 'contract'],
}

def classify(text):
    t = text.lower()
    for sig_type, kws in SIGNAL_PATTERNS.items():
        for kw in kws:
            if kw in t:
                return sig_type
    return 'PRODUCT'

def priority_from(score):
    if score >= 75: return 'HIGH'
    if score >= 55: return 'MEDIUM'
    return 'LOW'

def strategy_from(intent, conv):
    if intent > 0.75 and conv > 0.55:
        return 'BUILD_HEAVY', 'custom AI infra buildout', 'full architecture assessment', 'CTO / Head of AI', 'cold_email'
    if intent > 0.55 and conv > 0.35:
        return 'CO_BUILD', 'co-development with internal data team', 'joint ML pipeline optimization session', 'VP Engineering / Director Data', 'cold_email'
    return 'MONITOR', 'share AI insights and case studies', 'send domain-specific AI case study', 'Technical Leader / Director', 'linkedin'

# ── Company definitions ────────────────────────────────────────
# outsource_need: likelihood a company NEEDS to buy tech help vs. building it themselves
# 1.0 = no internal tech team, clear business problem → perfect customer
# 0.1 = deep-tech company that builds everything in-house → won't buy from us
COMPANIES = [
    {
        'name': 'Cropin Technology',
        'slug': 'cropin-technology',
        'industry': 'Agri-tech / Precision Farming',
        'domain': 'AI Precision Farming',
        'size': 'MID',
        'employees': 450,
        'region': 'Bengaluru, India',
        'internal_tech_strength': 0.65,
        'conversion_bias': 0.70,
        'competitor': False,
        'outsource_need': 0.70,  # Has some tech team but needs specialized data infra help
    },
    {
        'name': 'Bentley Systems',
        'slug': 'bentley-systems',
        'industry': 'Civil / Mechanical Engineering Software',
        'domain': 'Engineering Infrastructure Software',
        'size': 'LARGE',
        'employees': 5000,
        'region': 'Exton, PA, USA',
        'internal_tech_strength': 0.80,
        'conversion_bias': 0.65,
        'competitor': False,
        'outsource_need': 0.45,  # Large eng-software company, strong internal team
    },
    {
        'name': "Dr. Reddy's Laboratories",
        'slug': 'dr-reddys-laboratories',
        'industry': 'Pharmaceutical / Life Sciences',
        'domain': 'Pharma & Drug Manufacturing',
        'size': 'LARGE',
        'employees': 24000,
        'region': 'Hyderabad, India (NYSE: RDY)',
        'internal_tech_strength': 0.70,
        'conversion_bias': 0.82,
        'competitor': False,
        'outsource_need': 0.85,  # Pharma = huge data needs, outsources most IT/AI
    },
    {
        'name': 'Clari',
        'slug': 'clari',
        'industry': 'AI Revenue Intelligence / Sales Analytics',
        'domain': 'Revenue Operations & Sales AI',
        'size': 'MID',
        'employees': 750,
        'region': 'Sunnyvale, CA, USA',
        'internal_tech_strength': 0.92,
        'conversion_bias': 0.10,
        'competitor': True,
        'outsource_need': 0.0,
    },
    {
        'name': 'MindsDB',
        'slug': 'mindsdb',
        'industry': 'AI/ML Database',
        'domain': 'AI-in-Database Platform',
        'size': 'MID',
        'employees': 100,
        'region': 'San Francisco, CA, USA',
        'internal_tech_strength': 0.85,
        'conversion_bias': 0.88,
        'competitor': False,
        'outsource_need': 0.10,  # Deep-tech AI company — builds everything in-house, won't buy
    },
    {
        'name': 'Deenet Services',
        'slug': 'deenet-services',
        'industry': 'IT Services / Digital Solutions',
        'domain': 'IT Services & Digital Transformation',
        'size': 'SMALL',
        'employees': 80,
        'region': 'India',
        'internal_tech_strength': 0.40,
        'conversion_bias': 0.80,
        'competitor': False,
        'outsource_need': 0.72,  # IT services company — frequently buys SaaS/AI tools
    },
    {
        'name': 'Spotify',
        'slug': 'spotify',
        'industry': 'Music Streaming / Entertainment Tech',
        'domain': 'Audio Streaming & Podcast Platform',
        'size': 'LARGE',
        'employees': 9800,
        'region': 'Stockholm, Sweden',
        'internal_tech_strength': 0.92,
        'conversion_bias': 0.55,
        'competitor': False,
        'outsource_need': 0.18,  # Giant tech company — 1000+ engineers, builds everything
    },
    {
        'name': 'Fathima Stores',
        'slug': 'fathima-stores',
        'industry': 'Retail / Grocery',
        'domain': 'Retail Supermarket Chain',
        'size': 'SMALL',
        'employees': 200,
        'region': 'Kerala, India',
        'internal_tech_strength': 0.20,
        'conversion_bias': 0.82,
        'competitor': False,
        'outsource_need': 0.92,  # No tech team, strong need for inventory/demand analytics
    },
    {
        'name': 'MLM Constructions and Products',
        'slug': 'mlm-constructions',
        'industry': 'Civil Engineering / Construction',
        'domain': 'Construction & Building Materials',
        'size': 'SMALL',
        'employees': 120,
        'region': 'California, USA',
        'internal_tech_strength': 0.25,
        'conversion_bias': 0.80,
        'competitor': False,
        'outsource_need': 0.88,  # No tech team, clear need for project/cost analytics
    },
]

db = SessionLocal()

for cfg in COMPANIES:
    name    = cfg['name']
    slug    = cfg['slug']
    is_comp = cfg['competitor']
    print(f"\nSeeding: {name} (competitor={is_comp})")

    # ── Get signals from cache ──────────────────────────────
    entry   = CACHE.get(name, {})
    raw_sigs = entry.get('signals', {})
    meta    = entry.get('meta', {})
    dms     = entry.get('decision_makers', [])
    dm      = dms[0] if dms else {}
    # LLM-generated intel (from scrape_to_cache.py, if API key configured)
    llm_persona  = entry.get('llm_persona', {})
    llm_outreach = entry.get('llm_outreach', {})

    enriched = []
    for cat, items in raw_sigs.items():
        for item in items:
            enriched.append({
                'type':                classify(item.get('text', '')),
                'text':                item.get('text', ''),
                'recency_days':        item.get('recency_days', 90),
                'source':              item.get('source', cat),
                'verified':            item.get('verified', False),
                'verification_source': item.get('verification_source', ''),
            })

    # ── Scores ─────────────────────────────────────────────
    # Expansion: 3 strong signals = full marks
    expansion  = min(1.0, len([s for s in enriched if s['type'] in {'HIRING','FUNDING','PRODUCT','GTM'}]) / 3.0)
    strain     = round(expansion * 0.75 + len([s for s in enriched if s['type'] == 'INFRA']) * 0.1, 3)
    risk       = 0.90 if is_comp else 0.05
    pain_score = round(0.5 * expansion + 0.3 * strain + 0.2 * (1 - risk), 3)
    pain_level = 'HIGH' if pain_score > 0.70 else 'MEDIUM' if pain_score > 0.40 else 'LOW'

    best = {}
    for s in enriched:
        t = s['type']
        if t not in best or (s.get('recency_days') or 999) < (best[t].get('recency_days') or 999):
            best[t] = s
    key_signals = list(best.keys())[:3]

    # LOW internal_tech_strength = they can't build it → they BUY it from us
    capability_gap = round(1.0 - cfg['internal_tech_strength'], 3)
    # Intent floor of 0.35 — even with 0 scraped signals, company params still drive intent
    raw_intent = round(0.40 * expansion + 0.30 * strain + 0.30 * capability_gap, 3)
    intent     = round(max(raw_intent, 0.35 * capability_gap + 0.15), 3)
    conv     = round(cfg['conversion_bias'] * 0.75 + 0.25 * capability_gap, 3) if not is_comp else 0.08
    # MID/SMALL companies = recurring, sticky, long-term revenue
    deal_sz  = 0.55 if cfg['size'] == 'LARGE' else 0.80
    recurring_bonus = 0.05 if cfg['size'] in ('MID', 'SMALL') and not is_comp else 0.0
    raw_score = round(0.30 * intent + 0.45 * conv + 0.25 * deal_sz + recurring_bonus, 3) if not is_comp else 0.12
    # outsource_need: blended into final score (70% raw, 30% outsource signal)
    # This prevents outsource_need from crushing scores multiplicatively
    outsource_need = cfg.get('outsource_need', 0.5)
    opp_sc   = round(raw_score * 0.70 + outsource_need * 0.30, 3) if not is_comp else 0.12
    priority = priority_from(int(opp_sc * 100))
    score_int = int(opp_sc * 100) if not is_comp else 12

    strategy, offer, entry_pt, persona_def, channel = strategy_from(intent, conv)
    if is_comp:
        strategy, offer, entry_pt, persona_def, channel = 'AVOID', 'Do not target', 'N/A', 'N/A', 'none'

    dm_name = dm.get('name', '')
    # Use LLM persona role if available, else fall back to strategy template
    dm_role = llm_persona.get('role') or dm.get('role', persona_def)

    if is_comp:
        message = "[COMPETITOR — DO NOT OUTREACH]\n\n" + name + " builds AI-powered revenue intelligence — directly overlapping with Datavex's core offering.\n\nUse as competitive benchmark only."
        subject = f"[COMPETITOR] {name} — competitive analysis only"
    elif llm_outreach.get('email'):
        # █ LLM-generated outreach (grounded in scraped signals)
        message  = llm_outreach['email']
        subject  = llm_outreach.get('subject', f"{name} — quick idea on {entry_pt}")
    else:
        sig_map = {
            'HIRING':'rapid hiring and team expansion','FUNDING':'recent funding and capital deployment',
            'INFRA':'increasing infrastructure complexity','PRODUCT':'new product/platform launches',
            'GTM':'enterprise partnerships and go-to-market expansion'
        }
        signal_line = ' and '.join([sig_map.get(s,s) for s in key_signals[:2]]) or 'recent growth'
        angle = {'BUILD_HEAVY':'accelerate delivery and reduce infra burden','CO_BUILD':'augment your internal team to ship faster','MONITOR':'share insights and stay aligned'}.get(strategy,'explore collaboration')
        subject = f"{name} — quick idea on {entry_pt}"
        message = f"""Hi {dm_name or dm_role},

Noticed that {name} is seeing {signal_line} — signals that the team is scaling quickly.

We help companies at this stage {angle}, especially around {entry_pt}.

Would it be useful to start with a quick 20-min call?

– Datavex""".strip()

    receptivity_map = {'HIGH':'HIGH — ACT WITHIN 90 DAYS','MEDIUM':'MODERATE — ACT WITHIN 6 MONTHS','LOW':'LOW — MONITOR'}
    receptivity = 'COMPETITOR — DO NOT TARGET' if is_comp else receptivity_map.get(priority,'LOW — MONITOR')
    descriptor  = f"{cfg['industry']} · {cfg['employees']:,} employees · {cfg['size']} · {cfg['region']}"

    trace = [
        {'time':'00:01','agent':'TARGET_DISCOVERY','action':f"Found {name} — {cfg['industry']}, {cfg['size']}, {cfg['region']}"},
        {'time':'00:05','agent':'SIGNAL_EXTRACTION','action':f"Pain: {pain_level}, {len(enriched)} signals, {sum(1 for s in enriched if s['verified'])} verified"},
        {'time':'00:10','agent':'OPPORTUNITY_SCORING','action':f"Score: {score_int}/100, Priority: {priority}, Intent: {intent:.2f}"},
        {'time':'00:14','agent':'STRATEGY','action':f"Style: {strategy} — {offer}"},
        {'time':'00:18','agent':'DECISION_MAKER','action':f"Target: {dm_name} ({dm_role}) — entry: {entry_pt}"},
        {'time':'00:24','agent':'OUTREACH','action':f"Channel: {channel} · Subject: {subject}"},
    ]

    new_data = {
        'descriptor': descriptor, 'receptivity': receptivity,
        'pain_level': pain_level, 'pain_tags': key_signals,
        'competitor': is_comp,
        'competitor_note': meta.get('competitor_note', f"⚠️ Potential Competitor — Not a Target Client. {name} operates in the same space as Datavex." if is_comp else ''),
        'signal_counts': {'verified': sum(1 for s in enriched if s.get('verified')), 'unverified': sum(1 for s in enriched if not s.get('verified')), 'total': len(enriched)},
        'agent1': {'company_name':name,'domain':cfg['domain'],'industry':cfg['industry'],'size':cfg['size'],'estimated_employees':cfg['employees'],'region':cfg['region']},
        'agent2': {'fit_type':'COMPETITOR' if is_comp else 'TARGET','company_state':'MATURE' if is_comp else 'SCALE_UP','expansion_score':expansion,'strain_score':min(1.0,strain),'risk_score':risk,'pain_score':pain_score,'pain_level':pain_level,'signals':enriched},
        'agent3': {
            'priority': priority, 'opportunity_score': opp_sc,
            'intent_score': intent, 'conversion_score': conv,
            'deal_size_score': deal_sz, 'expansion_score': expansion,
            'strain_score': min(1.0, strain), 'risk_score': risk,
            'key_signals': key_signals,
            'summary': f"{name} shows {int(intent*100)}% intent, {int(conv*100)}% conversion, {int(deal_sz*100)}% deal size. Key signals: {' | '.join(key_signals)}.",
            'llm_reasoning': entry.get('llm_reasoning', ''),   # from scrape_to_cache LLM run
        },
        'agent35': {'buying_style':strategy,'tech_strength':cfg['internal_tech_strength'],'offer':offer,'entry_point':entry_pt,'strategy_note':f"{name} → {strategy}"},
        'agent4': {'priority':priority,'strategy':strategy,'recommended_offer':offer,'entry_point':entry_pt,'intent_score':intent,'conversion_score':conv,'deal_size_score':deal_sz,'risk_score':risk,'key_signals':key_signals},
        'agent5': {
            'persona': dm_role,
            'channel': channel,
            'subject': subject,
            'message': message,
            'linkedin_dm': llm_outreach.get('linkedin_dm', ''),
            'llm_generated': bool(llm_outreach.get('email')),
            'priority': priority,
            'conversion_score': conv,
            'deal_size_score': deal_sz,
        },
        'financials': {'quarters':[],'margin':[],'revenue':[]}, 'hiring': [],
        'scoreBreakdown': [{'label':'Intent','value':int(intent*35),'max':35},{'label':'Conversion','value':int(conv*25),'max':25},{'label':'Deal Size','value':int(deal_sz*20),'max':20},{'label':'Signal Depth','value':int(expansion*20),'max':20}],
        'timeline': [], 'painClusters': [],
        'decisionMaker': {'name':dm_name,'role':dm_role,'messaging':{'angle':offer,'vocab':key_signals,'tone':strategy.lower()}},
        'outreach': {'email':message if not is_comp else '','opener':subject,'footnote':f"Channel: {channel}"},
        'capabilityMatch': [], 'strongestMatch': {}, 'trace': trace,
        'agent6': {},
    }

    # ── Agent 6: What to Sell (RAG + Ollama) ──────────────
    if HAS_AGENT6 and not is_comp:
        try:
            a4_decision = [{
                'company_name': name, 'strategy': strategy,
                'recommended_offer': offer, 'entry_point': entry_pt,
                'intent_score': intent, 'conversion_score': conv,
                'deal_size_score': deal_sz, 'risk_score': 0.05,
                'priority': priority, 'key_signals': key_signals,
            }]
            a2_sig = [{
                'company_name': name, 'company_state': 'SCALE_UP',
                'meta': {'industry': cfg['industry'], 'size': cfg['size']},
                'pain_level': 'HIGH' if priority == 'HIGH' else 'MEDIUM',
                'signals': enriched[:5],
            }]
            a6_results = agent6_recommender.run(a4_decision, a2_sig)
            if a6_results:
                new_data['agent6'] = a6_results[0]
                print(f"  Agent6: {a6_results[0].get('lead_service','?')} ({a6_results[0].get('confidence','?')})")
        except Exception as e:
            print(f"  Agent6 failed: {e}")

    existing = db.query(CompanyRecord).filter(CompanyRecord.id == slug).first()
    if existing:
        existing.score=score_int; existing.confidence=priority; existing.coverage=int(expansion*100)
        existing.descriptor=descriptor; existing.data=new_data; existing.updated_at=utcnow()
        flag_modified(existing, 'data')
        print(f"  Updated: score={score_int}, priority={priority}")
    else:
        db.add(CompanyRecord(id=slug,scan_id=None,name=name,descriptor=descriptor,score=score_int,confidence=priority,coverage=int(expansion*100),data=new_data,created_at=utcnow(),updated_at=utcnow()))
        print(f"  Created: score={score_int}, priority={priority}")

db.commit()
db.close()
print("\n✅ Seed complete — all companies loaded.")
print("   Run: cd backend && uvicorn app.main:app --reload --port 8000")
