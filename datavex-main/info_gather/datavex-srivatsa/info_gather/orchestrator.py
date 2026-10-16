"""
DataVex B2B Intelligence Engine — Main Orchestrator
Usage:
    python orchestrator.py --company "Notion" --domain notion.so --github makenotion
    python orchestrator.py --demo
"""
import argparse
import json
import os
from datetime import datetime
from loguru import logger

from scrapers.earnings        import search_edgar_transcripts, scrape_ir_page_transcripts
from scrapers.jobs            import scrape_careers_page
from scrapers.tech_stack      import detect_tech_stack
from scrapers.github_scraper  import scrape_github_org, find_github_org
from scrapers.financials      import (
    scrape_yahoo_finance, scrape_layoff_news,
    scrape_funding_news, compute_fiscal_pressure
)
from scrapers.press_releases  import scrape_press_releases
from models.schema import (
    init_db, Company, EarningsTranscript, JobPosting,
    TechStack, GithubData, FinancialData, LayoffEvent,
    FundingRound, PressRelease
)


def analyze_company(
    company_name: str,
    domain: str,
    ticker: str | None = None,
    github_org: str | None = None,
    careers_url: str | None = None,
    ir_url: str | None = None,
    news_url: str | None = None,
    db_session=None,
    save_to_db: bool = True,
) -> dict:
    logger.info(f"\n{'='*60}")
    logger.info(f"Analyzing: {company_name} ({domain})")
    logger.info(f"{'='*60}")

    profile = {
        "company_name": company_name,
        "domain":       domain,
        "is_public":    ticker is not None,
        "analyzed_at":  datetime.utcnow().isoformat(),
    }

    # ── 1. Earnings Transcripts ───────────────────────────────────────
    logger.info("[1/7] Earnings transcripts...")
    transcripts = []
    if ticker:
        transcripts = search_edgar_transcripts(ticker, limit=4)
    if ir_url and len(transcripts) < 2:
        transcripts += scrape_ir_page_transcripts(ir_url, company_name)
    profile["transcripts"] = transcripts
    if not transcripts and not ticker:
        logger.info("  → Private company — no public filings (expected)")
    else:
        logger.success(f"  → {len(transcripts)} transcripts")

    # ── 2. Job Postings ───────────────────────────────────────────────
    logger.info("[2/7] Job postings...")
    careers = careers_url or f"https://{domain}/careers"
    jobs = scrape_careers_page(careers, company_name, limit=30)
    profile["job_postings"] = jobs

    pivot_kws, tech_debt_kws, fiscal_kws = [], [], []
    dept_counts = {}
    for j in jobs:
        kw = j.get("keywords", {})
        pivot_kws     += kw.get("pivot", [])
        tech_debt_kws += kw.get("tech_debt", [])
        fiscal_kws    += kw.get("fiscal", [])

        dept = j.get("department", "Other")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    profile["hiring_signals"] = {
        "pivot_keywords":     list(set(pivot_kws)),
        "tech_debt_keywords": list(set(tech_debt_kws)),
        "fiscal_keywords":    list(set(fiscal_kws)),
        "total_jobs":         len(jobs),
        "departments":        dict(sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)),
        "engineering_ratio":  round(dept_counts.get("Engineering", 0) / max(len(jobs), 1), 2),
    }
    logger.success(f"  → {len(jobs)} jobs | Pivot: {list(set(pivot_kws))[:5]}")

    # ── 3. Tech Stack ─────────────────────────────────────────────────
    logger.info("[3/7] Tech stack detection...")
    stack = detect_tech_stack(domain, company_name)
    profile["tech_stack"] = stack
    logger.success(f"  → {stack.get('frameworks', [])} | Legacy: {stack.get('debt_signals',{}).get('detected_legacy_tech',[])}")

    # ── 4. GitHub ─────────────────────────────────────────────────────
    logger.info("[4/7] GitHub analysis...")
    if not github_org:
        github_org = find_github_org(company_name)
    gh_data = {}
    if github_org:
        gh_data = scrape_github_org(github_org, company_name)
        logger.success(f"  → {gh_data.get('total_repos',0)} repos | {gh_data.get('total_open_issues',0)} issues | Debt: {gh_data.get('github_debt',{}).get('label')}")

    else:
        logger.info("  → No GitHub org found")
    profile["github"] = gh_data

    # ── 5. Financials ─────────────────────────────────────────────────
    logger.info("[5/7] Financial data...")
    financials = []
    if ticker:
        financials = scrape_yahoo_finance(ticker, company_name)
        logger.success(f"  → {len(financials)} quarters")
    else:
        logger.info("  → Private company — no public financials")
    profile["financials"] = financials

    # ── 6. Layoffs & Funding ──────────────────────────────────────────
    logger.info("[6/7] Layoffs & funding news...")
    layoffs = scrape_layoff_news(company_name)
    funding = scrape_funding_news(company_name)
    profile["layoffs"] = layoffs
    profile["funding"] = funding
    logger.success(f"  → {len(layoffs)} layoff signals | {len(funding)} funding signals")

    # ── 7. Press Releases ─────────────────────────────────────────────
    logger.info("[7/7] Press releases...")
    news_page = news_url or f"https://{domain}/news"
    press = scrape_press_releases(company_name, domain, news_page, limit=20)
    profile["press_releases"] = press
    logger.success(f"  → {len(press)} press releases")

    # ── Composite Scores ──────────────────────────────────────────────
    profile["fiscal_pressure"] = compute_fiscal_pressure(financials, layoffs, funding)
    profile["technical_debt"]  = _compute_tech_debt_score(stack, gh_data, jobs)
    profile["recent_pivot"]    = _compute_pivot_score(press, jobs, transcripts)
    profile["opportunity_score"] = _compute_opportunity_score(profile)
    profile["llm_ready_summary"] = _build_llm_summary(profile)

    logger.success(f"\n✓ {company_name} complete")
    logger.info(f"  Fiscal Pressure : {profile['fiscal_pressure']['fiscal_pressure_score']}/10  ({profile['fiscal_pressure']['fiscal_pressure_label']})")
    logger.info(f"  Technical Debt  : {profile['technical_debt']['score']}/10  ({profile['technical_debt']['label']})")
    logger.info(f"  Pivot Activity  : {profile['recent_pivot']['score']}/10  ({profile['recent_pivot']['label']})")
    logger.info(f"  Opportunity     : {profile['opportunity_score']}/10")

    if save_to_db and db_session:
        _persist_to_db(profile, db_session)

    return profile


# ── Scoring ───────────────────────────────────────────────────────────────────

def _compute_tech_debt_score(stack: dict, gh: dict, jobs: list[dict]) -> dict:
    score, signals = 0, []

    legacy = stack.get("debt_signals", {}).get("detected_legacy_tech", [])
    if legacy:
        score += min(3, len(legacy))
        signals.append(f"Legacy tech: {legacy}")

    if gh:
        gh_score = gh.get("github_debt", {}).get("score", 0)
        score += min(3, gh_score // 2)
        if gh_score > 3:
            signals.append(f"GitHub debt: {gh_score}/10")
        legacy_repos = gh.get("legacy_signals", [])
        if legacy_repos:
            signals.append(f"Legacy repos: {[r['signal'] for r in legacy_repos[:3]]}")

    debt_kws = list(set(k for j in jobs for k in j.get("keywords", {}).get("tech_debt", [])))
    if debt_kws:
        score += min(4, len(debt_kws))
        signals.append(f"Modernisation hiring: {debt_kws[:5]}")

    score = min(10, score)
    return {"score": score, "label": _label(score), "signals": signals}


def _compute_pivot_score(press: list, jobs: list, transcripts: list) -> dict:
    score, signals = 0, []

    all_pr = list(set(s for pr in press for s in pr.get("pivot_signals", [])))
    if all_pr:
        score += min(4, len(all_pr))
        signals.append(f"Press signals: {all_pr[:6]}")

    pivot_kws = list(set(k for j in jobs for k in j.get("keywords", {}).get("pivot", [])))
    if pivot_kws:
        score += min(4, len(pivot_kws))
        signals.append(f"Hiring pivot: {pivot_kws[:5]}")

    pivot_count = sum(
        1 for t in transcripts
        for term in ["ai-first","strategic","transformation","pivot",
                     "expand","realign","generative","agentic"]
        if term in t.get("raw_text","").lower()
    )
    if pivot_count:
        score += min(2, pivot_count // 2)
        signals.append(f"Transcript pivot mentions: {pivot_count}")

    score = min(10, score)
    return {"score": score, "label": _label(score), "signals": signals}


def _compute_opportunity_score(profile: dict) -> float:
    """
    Weighted composite 0-10.

    Key insight: fiscal pressure is a DOUBLE-EDGED signal.
    - High fiscal pressure (layoffs, revenue decline) = urgency to buy
    - Low fiscal pressure with high pivot = growth budget, buying to transform
    Both are good sales signals. Pure 0 pressure = less urgent.

    Pivot is the strongest signal for timing.
    Tech debt = pain point to sell against.
    Hiring volume = budget open.
    """
    fiscal  = profile["fiscal_pressure"]["fiscal_pressure_score"]
    debt    = profile["technical_debt"]["score"]
    pivot   = profile["recent_pivot"]["score"]
    layoffs = len(profile.get("layoffs", []))
    funding = len(profile.get("funding", []))
    jobs    = len(profile.get("job_postings", []))

    # Fiscal signal: treat both high pressure AND strong funding as positive
    # (funded company spending, OR distressed company cutting costs = both buying)
    fiscal_signal = fiscal  # high pressure = urgency
    funded_bonus  = min(3, funding * 0.5)  # recent funding = budget

    hiring_bonus = min(2, jobs / 15)

    score = (
        pivot          * 0.35 +
        debt           * 0.20 +
        fiscal_signal  * 0.15 +
        funded_bonus   * 0.15 +
        hiring_bonus   * 0.10 +
        min(10, layoffs * 2) * 0.05
    )
    return round(min(10, score), 2)


def _label(score: int) -> str:
    if score >= 8: return "Critical"
    if score >= 6: return "High"
    if score >= 4: return "Medium"
    if score >= 2: return "Low"
    return "Minimal"


def _build_llm_summary(profile: dict) -> dict:
    hs = profile.get("hiring_signals", {})
    gh = profile.get("github", {})

    # Collect trigger signals: layoffs + strong pivot press releases
    trigger_signals = []
    for l in profile.get("layoffs", [])[:3]:
        trigger_signals.append(l.get("headline", ""))
    for pr in profile.get("press_releases", []):
        if pr.get("pivot_signals"):
            trigger_signals.append(pr.get("title", ""))
    for f in profile.get("funding", [])[:2]:
        if f.get("amount_usd") and f["amount_usd"] > 100_000_000:
            trigger_signals.append(f.get("headline", ""))

    top_funding = profile.get("funding", [])
    funding_status = (
        top_funding[0].get("headline", "Unknown")[:100]
        if top_funding else "Unknown"
    )

    return {
        "company_name":          profile["company_name"],
        "fiscal_pressure_score": profile["fiscal_pressure"]["fiscal_pressure_score"],
        "fiscal_signals":        profile["fiscal_pressure"]["signals"],
        "technical_debt_score":  profile["technical_debt"]["score"],
        "debt_signals":          profile["technical_debt"]["signals"],
        "recent_pivot":          profile["recent_pivot"]["signals"],
        "pivot_score":           profile["recent_pivot"]["score"],
        "funding_status":        funding_status,
        "trigger_signals":       list(dict.fromkeys(trigger_signals))[:5],  # dedup, top 5
        "revenue_trend":         "public" if profile.get("is_public") else "private",
        "trigger_recency_days":  30,
        "total_jobs_posted":     hs.get("total_jobs", 0),
        "top_hiring_dept":       list(hs.get("departments", {}).keys())[:3],
        "pivot_hiring_keywords": hs.get("pivot_keywords", [])[:5],
        "github_debt_score":     gh.get("github_debt", {}).get("score", "N/A"),
        "opportunity_score":     profile["opportunity_score"],
    }


# ── DB persistence ────────────────────────────────────────────────────────────

def _persist_to_db(profile: dict, session):
    name = profile["company_name"]
    try:
        if not session.query(Company).filter_by(name=name).first():
            session.add(Company(name=name, domain=profile["domain"]))
        for t in profile.get("transcripts", []):
            session.add(EarningsTranscript(company_name=name, quarter=t.get("quarter",""),
                raw_text=t.get("raw_text",""), source_url=t.get("source_url","")))
        for j in profile.get("job_postings", []):
            session.add(JobPosting(company_name=name, role_title=j.get("role_title",""),
                department=j.get("department",""), description=j.get("description",""),
                keywords=j.get("keywords",{}), posted_date=j.get("posted_date",""),
                source=j.get("source","")))
        for f in profile.get("financials", []):
            session.add(FinancialData(company_name=name, ticker=f.get("ticker",""),
                quarter=f.get("quarter",""), revenue=f.get("revenue"),
                operating_margin=f.get("operating_margin"),
                gross_margin=f.get("gross_margin"),
                net_income=f.get("net_income"), source=f.get("source","")))
        for l in profile.get("layoffs", []):
            session.add(LayoffEvent(company_name=name, date=l.get("date",""),
                headcount=l.get("headcount"), percentage=l.get("percentage"),
                source_url=l.get("source_url","")))
        for f in profile.get("funding", []):
            session.add(FundingRound(company_name=name, round_type=f.get("round_type",""),
                amount_usd=f.get("amount_usd"), date=f.get("date",""),
                investors=f.get("investors",[]), source_url=f.get("source_url","")))
        for pr in profile.get("press_releases", []):
            session.add(PressRelease(company_name=name, title=pr.get("title",""),
                content=pr.get("content",""), published_date=pr.get("published_date",""),
                source_url=pr.get("source_url","")))
        session.commit()
        logger.success(f"[{name}] Saved to DB")
    except Exception as e:
        session.rollback()
        logger.error(f"DB save failed: {e}")


# ── Demo companies ────────────────────────────────────────────────────────────

DEMO_COMPANIES = [
    {"company_name": "Notion",   "domain": "notion.so",    "ticker": None,  "github_org": "makenotion"},
    {"company_name": "Linear",   "domain": "linear.app",   "ticker": None,  "github_org": "linear"},
    {"company_name": "Retool",   "domain": "retool.com",   "ticker": None,  "github_org": "tryretool"},
    {"company_name": "Airtable", "domain": "airtable.com", "ticker": None,  "github_org": "Airtable"},
    {"company_name": "Figma",    "domain": "figma.com",    "ticker": "FIG", "github_org": "figma"},
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DataVex B2B Intelligence Scraper")
    parser.add_argument("--company",  help="Company name")
    parser.add_argument("--domain",   help="Company domain")
    parser.add_argument("--ticker",   help="Stock ticker")
    parser.add_argument("--github",   help="GitHub org slug")
    parser.add_argument("--careers",  help="Careers page URL")
    parser.add_argument("--ir",       help="Investor relations URL")
    parser.add_argument("--news",     help="News page URL")
    parser.add_argument("--demo",     action="store_true")
    parser.add_argument("--output",   default="profile.json")
    args = parser.parse_args()

    SessionFactory = init_db()
    session = SessionFactory()

    if args.demo:
        profiles = []
        for c in DEMO_COMPANIES:
            p = analyze_company(**c, db_session=session, save_to_db=True)
            profiles.append(p)
        with open("demo_profiles.json", "w") as f:
            json.dump(profiles, f, indent=2, default=str)
        logger.success("Done → demo_profiles.json")

    elif args.company and args.domain:
        profile = analyze_company(
            company_name=args.company, domain=args.domain,
            ticker=args.ticker, github_org=args.github,
            careers_url=args.careers, ir_url=args.ir, news_url=args.news,
            db_session=session, save_to_db=True,
        )
        with open(args.output, "w") as f:
            json.dump(profile, f, indent=2, default=str)
        logger.success(f"Done → {args.output}")
    else:
        parser.print_help()
