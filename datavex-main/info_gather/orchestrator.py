"""
DataVex B2B Intelligence Engine — Main Orchestrator
Usage:
    python orchestrator.py --company "Infosys" --domain infosys.com --ticker INFY

For hackathon demo mode (pre-load 5 companies):
    python orchestrator.py --demo
"""
import argparse
import json
import os
from datetime import datetime
from loguru import logger

# Scrapers
from scrapers.earnings        import search_edgar_transcripts, scrape_ir_page_transcripts
from scrapers.jobs            import scrape_careers_page
from scrapers.tech_stack      import detect_tech_stack
from scrapers.github_scraper  import scrape_github_org, find_github_org
from scrapers.financials      import (
    scrape_yahoo_finance, scrape_layoff_news,
    scrape_funding_news, compute_fiscal_pressure
)
from scrapers.press_releases  import scrape_press_releases

# DB
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
    """
    Full pipeline: scrape all sources for a company and return structured profile.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Starting analysis: {company_name} ({domain})")
    logger.info(f"{'='*60}")

    profile = {
        "company_name": company_name,
        "domain": domain,
        "analyzed_at": datetime.utcnow().isoformat(),
    }

    # ── 1. Earnings Transcripts ───────────────────────────────────────
    logger.info("[1/7] Fetching earnings transcripts...")
    transcripts = []
    if ticker:
        transcripts = search_edgar_transcripts(ticker, limit=4)
    if ir_url and len(transcripts) < 2:
        transcripts += scrape_ir_page_transcripts(ir_url, company_name)
    profile["transcripts"] = transcripts
    logger.success(f"  → {len(transcripts)} transcripts found")

    # ── 2. Job Postings ───────────────────────────────────────────────
    logger.info("[2/7] Scraping job postings...")
    careers = careers_url or f"https://{domain}/careers"
    jobs = scrape_careers_page(careers, company_name, limit=25)
    profile["job_postings"] = jobs
    logger.success(f"  → {len(jobs)} job postings found")

    # Aggregate keyword signals across all jobs
    pivot_kws    = []
    tech_debt_kws = []
    for j in jobs:
        pivot_kws    += j.get("keywords", {}).get("pivot", [])
        tech_debt_kws += j.get("keywords", {}).get("tech_debt", [])
    profile["hiring_signals"] = {
        "pivot_keywords":     list(set(pivot_kws)),
        "tech_debt_keywords": list(set(tech_debt_kws)),
        "total_jobs":         len(jobs),
        "departments":        _count_departments(jobs),
    }

    # ── 3. Tech Stack ─────────────────────────────────────────────────
    logger.info("[3/7] Detecting tech stack...")
    stack = detect_tech_stack(domain, company_name)
    profile["tech_stack"] = stack
    logger.success(f"  → Frameworks: {stack.get('frameworks', [])}")

    # ── 4. GitHub ─────────────────────────────────────────────────────
    logger.info("[4/7] Scanning GitHub...")
    if not github_org:
        github_org = find_github_org(company_name)
    gh_data = {}
    if github_org:
        gh_data = scrape_github_org(github_org, company_name)
    profile["github"] = gh_data
    logger.success(f"  → {gh_data.get('total_repos', 0)} repos, "
                   f"{gh_data.get('total_open_issues', 0)} open issues")

    # ── 5. Financials ─────────────────────────────────────────────────
    logger.info("[5/7] Fetching financial data...")
    financials = []
    if ticker:
        financials = scrape_yahoo_finance(ticker, company_name)
    profile["financials"] = financials
    logger.success(f"  → {len(financials)} quarters of data")

    # ── 6. Layoffs & Funding ──────────────────────────────────────────
    logger.info("[6/7] Checking layoffs & funding...")
    layoffs  = scrape_layoff_news(company_name)
    funding  = scrape_funding_news(company_name)
    profile["layoffs"]  = layoffs
    profile["funding"]  = funding
    logger.success(f"  → {len(layoffs)} layoff events, {len(funding)} funding rounds")

    # ── 7. Press Releases ─────────────────────────────────────────────
    logger.info("[7/7] Collecting press releases...")
    news_page = news_url or f"https://{domain}/news"
    press     = scrape_press_releases(company_name, domain, news_page, limit=20)
    profile["press_releases"] = press
    logger.success(f"  → {len(press)} press releases")

    # ── Composite Scores ──────────────────────────────────────────────
    logger.info("Computing composite scores...")
    profile["fiscal_pressure"] = compute_fiscal_pressure(financials, layoffs, funding)

    tech_debt_score = _compute_tech_debt_score(stack, gh_data, jobs)
    profile["technical_debt"] = tech_debt_score

    pivot_score = _compute_pivot_score(press, jobs, transcripts)
    profile["recent_pivot"] = pivot_score

    # Final opportunity score for the LLM evaluator
    profile["opportunity_score"] = _compute_opportunity_score(
        profile["fiscal_pressure"]["fiscal_pressure_score"],
        tech_debt_score["score"],
        pivot_score["score"],
        layoffs,
        funding,
    )

    logger.success(f"\n[{company_name}] Analysis complete!")
    logger.info(f"  Fiscal Pressure : {profile['fiscal_pressure']['fiscal_pressure_score']}/10")
    logger.info(f"  Technical Debt  : {tech_debt_score['score']}/10")
    logger.info(f"  Pivot Activity  : {pivot_score['score']}/10")
    logger.info(f"  Opportunity     : {profile['opportunity_score']}/10")

    # ── Save to DB ────────────────────────────────────────────────────
    if save_to_db and db_session:
        _persist_to_db(profile, db_session)

    return profile


def _compute_tech_debt_score(stack: dict, gh: dict, jobs: list[dict]) -> dict:
    score = 0
    signals = []

    # Stack legacy signals
    legacy = stack.get("debt_signals", {}).get("detected_legacy_tech", [])
    score += min(3, len(legacy))
    if legacy:
        signals.append(f"Legacy tech: {legacy}")

    # GitHub debt
    gh_score = gh.get("github_debt", {}).get("score", 0) if gh else 0
    score += min(3, gh_score // 2)
    if gh_score > 4:
        signals.append(f"GitHub debt score: {gh_score}/10")

    # Hiring signals
    debt_kws = []
    for j in jobs:
        debt_kws += j.get("keywords", {}).get("tech_debt", [])
    if debt_kws:
        score += min(4, len(set(debt_kws)))
        signals.append(f"Job posting signals: {list(set(debt_kws))[:5]}")

    score = min(10, score)
    return {
        "score": score,
        "label": _score_to_label(score),
        "signals": signals,
    }


def _compute_pivot_score(press: list, jobs: list, transcripts: list) -> dict:
    score = 0
    signals = []

    # Press release pivot signals
    all_pr_signals = []
    for pr in press:
        all_pr_signals += pr.get("pivot_signals", [])
    if all_pr_signals:
        score += min(4, len(set(all_pr_signals)))
        signals.append(f"PR signals: {list(set(all_pr_signals))[:5]}")

    # Job posting pivot signals
    pivot_kws = []
    for j in jobs:
        pivot_kws += j.get("keywords", {}).get("pivot", [])
    if pivot_kws:
        score += min(3, len(set(pivot_kws)))
        signals.append(f"Hiring pivot: {list(set(pivot_kws))[:5]}")


    # Transcript keyword count (basic)
    pivot_terms_in_transcripts = 0
    for t in transcripts:
        text = t.get("raw_text", "").lower()
        for term in ["ai-first", "strategic", "transformation", "pivot", "expand", "realign"]:
            if term in text:
                pivot_terms_in_transcripts += 1
    if pivot_terms_in_transcripts:
        score += min(3, pivot_terms_in_transcripts // 2)
        signals.append(f"Transcript pivot mentions: {pivot_terms_in_transcripts}")

    score = min(10, score)
    return {
        "score": score,
        "label": _score_to_label(score),
        "signals": signals,
    }


def _compute_opportunity_score(fiscal: float, debt: float, pivot: float,
                                layoffs: list, funding: list) -> float:
    """Weighted composite score — mirrors the LLM evaluator's input."""
    score = (
        fiscal * 0.35 +
        debt   * 0.30 +
        pivot  * 0.20 +
        min(10, len(layoffs) * 2) * 0.10 +
        min(10, len(funding)  * 3) * 0.05
    )
    return round(score, 2)


def _count_departments(jobs: list) -> dict:
    counts = {}
    for j in jobs:
        dept = j.get("department", "Other")
        counts[dept] = counts.get(dept, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def _score_to_label(score: int) -> str:
    if score >= 8: return "Critical"
    if score >= 6: return "High"
    if score >= 4: return "Medium"
    if score >= 2: return "Low"
    return "Minimal"


def _persist_to_db(profile: dict, session):
    """Save all scraped data to the database."""
    company_name = profile["company_name"]
    try:
        # Upsert company
        company = session.query(Company).filter_by(name=company_name).first()
        if not company:
            company = Company(name=company_name, domain=profile["domain"])
            session.add(company)

        # Transcripts
        for t in profile.get("transcripts", []):
            session.add(EarningsTranscript(
                company_name=company_name,
                quarter=t.get("quarter", ""),
                raw_text=t.get("raw_text", ""),
                source_url=t.get("source_url", ""),
            ))

        # Jobs
        for j in profile.get("job_postings", []):
            session.add(JobPosting(
                company_name=company_name,
                role_title=j.get("role_title", ""),
                department=j.get("department", ""),
                description=j.get("description", ""),
                keywords=j.get("keywords", {}),
                posted_date=j.get("posted_date", ""),
                source=j.get("source", ""),
            ))

        # Financials
        for f in profile.get("financials", []):
            session.add(FinancialData(
                company_name=company_name,
                ticker=f.get("ticker", ""),
                quarter=f.get("quarter", ""),
                revenue=f.get("revenue"),
                operating_margin=f.get("operating_margin"),
                gross_margin=f.get("gross_margin"),
                net_income=f.get("net_income"),
                source=f.get("source", ""),
            ))

        # Layoffs
        for l in profile.get("layoffs", []):
            session.add(LayoffEvent(
                company_name=company_name,
                date=l.get("date", ""),
                headcount=l.get("headcount"),
                percentage=l.get("percentage"),
                source_url=l.get("source_url", ""),
            ))

        # Funding
        for f in profile.get("funding", []):
            session.add(FundingRound(
                company_name=company_name,
                round_type=f.get("round_type", ""),
                amount_usd=f.get("amount_usd"),
                date=f.get("date", ""),
                investors=f.get("investors", []),
                source_url=f.get("source_url", ""),
            ))

        # Press releases
        for pr in profile.get("press_releases", []):
            session.add(PressRelease(
                company_name=company_name,
                title=pr.get("title", ""),
                content=pr.get("content", ""),
                published_date=pr.get("published_date", ""),
                source_url=pr.get("source_url", ""),
            ))

        session.commit()
        logger.success(f"[{company_name}] Data saved to DB")

    except Exception as e:
        session.rollback()
        logger.error(f"DB save failed: {e}")


# ── Demo Companies (Hackathon Pre-load) ──────────────────────────────────────
DEMO_COMPANIES = [
    {
        "company_name": "Notion",
        "domain":       "notion.so",
        "ticker":       None,
        "github_org":   "makenotion",
        "careers_url":  "https://www.notion.so/careers",
    },
    {
        "company_name": "Linear",
        "domain":       "linear.app",
        "ticker":       None,
        "github_org":   "linear",
        "careers_url":  "https://linear.app/careers",
    },
    {
        "company_name": "Retool",
        "domain":       "retool.com",
        "ticker":       None,
        "github_org":   "tryretool",
        "careers_url":  "https://retool.com/careers",
    },
    {
        "company_name": "Airtable",
        "domain":       "airtable.com",
        "ticker":       None,
        "github_org":   "Airtable",
        "careers_url":  "https://airtable.com/careers",
    },
    {
        "company_name": "Figma",
        "domain":       "figma.com",
        "ticker":       None,
        "github_org":   "figma",
        "careers_url":  "https://www.figma.com/careers",
    },
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DataVex B2B Intelligence Scraper")
    parser.add_argument("--company",     help="Company name")
    parser.add_argument("--domain",      help="Company domain (e.g. infosys.com)")
    parser.add_argument("--ticker",      help="Stock ticker (optional, for public companies)")
    parser.add_argument("--github",      help="GitHub org name (optional)")
    parser.add_argument("--careers",     help="Careers page URL (optional)")
    parser.add_argument("--ir",          help="Investor relations URL (optional)")
    parser.add_argument("--news",        help="News page URL (optional)")
    parser.add_argument("--demo",        action="store_true", help="Run all demo companies")
    parser.add_argument("--output",      default="profile.json", help="Output JSON file")
    args = parser.parse_args()

    # Init DB
    SessionFactory = init_db()
    session = SessionFactory()

    if args.demo:
        logger.info("Running demo mode — analyzing 5 pre-selected companies")
        profiles = []
        for company in DEMO_COMPANIES:
            profile = analyze_company(**company, db_session=session, save_to_db=True)
            profiles.append(profile)
        with open("demo_profiles.json", "w") as f:
            json.dump(profiles, f, indent=2, default=str)
        logger.success("Demo complete! Profiles saved to demo_profiles.json")

    elif args.company and args.domain:
        profile = analyze_company(
            company_name=args.company,
            domain=args.domain,
            ticker=args.ticker,
            github_org=args.github,
            careers_url=args.careers,
            ir_url=args.ir,
            news_url=args.news,
            db_session=session,
            save_to_db=True,
        )
        with open(args.output, "w") as f:
            json.dump(profile, f, indent=2, default=str)
        logger.success(f"Profile saved to {args.output}")

    else:
        parser.print_help()
