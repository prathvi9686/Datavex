#!/usr/bin/env python3
"""
DataVex — Scraper-to-Cache Adapter
Runs the Srivatsa scrapers for target companies and writes
clean, typed signals into datavex_pipeline/search_cache.json.

Usage:
    cd /home/nishanth/projects/datavex
    .venv/bin/python scrape_to_cache.py

Then run:
    python seed_db.py
"""
import sys, os, json, re, time, random
from datetime import datetime, timezone

# ── Path setup ─────────────────────────────────────────────────
ROOT     = os.path.dirname(os.path.abspath(__file__))
SCRAPER_DIR = os.path.join(ROOT, "info_gather", "datavex-srivatsa", "info_gather")
PIPELINE_DIR = os.path.join(ROOT, "datavex_pipeline")
CACHE_PATH  = os.path.join(ROOT, "datavex_pipeline", "search_cache.json")

sys.path.insert(0, SCRAPER_DIR)
sys.path.insert(0, PIPELINE_DIR)  # for datavex_pipeline/config.py LLM client

# ── Import scrapers ────────────────────────────────────────────
from scrapers.tech_stack    import detect_tech_stack
from scrapers.press_releases import scrape_press_releases
from scrapers.financials    import scrape_yahoo_finance, scrape_funding_news, scrape_layoff_news

try:
    from scrapers.jobs import scrape_careers_page
    HAS_JOBS = True
except Exception:
    HAS_JOBS = False

# ── LLM client (from datavex_pipeline/config.py) ─────────────
try:
    from config import llm_call_with_retry, OFFLINE_MODE
    if OFFLINE_MODE:
        print("[LLM] No API key found — LLM persona/outreach generation SKIPPED (OFFLINE mode)")
    else:
        print("[LLM] API key detected — LLM persona/outreach generation ENABLED")
except Exception as e:
    OFFLINE_MODE = True
    llm_call_with_retry = None
    print(f"[LLM] Could not import config: {e} — LLM generation SKIPPED")

# ── Company definitions ────────────────────────────────────────
# For each company define: name, domain, ticker (None if private),
# careers_url (None if no ATS), size, industry, region, employees, competitor
COMPANIES = [
    {
        "name":        "Spotify",
        "slug":        "spotify",
        "domain":      "spotify.com",
        "ticker":      "SPOT",
        "careers_url": "https://www.lifeatspotify.com/jobs",
        "news_url":    "https://newsroom.spotify.com",
        "industry":    "Music Streaming / Entertainment Tech",
        "domain_display": "Audio Streaming & Podcast Platform",
        "size":        "LARGE",
        "employees":   9800,
        "region":      "Stockholm, Sweden (NASDAQ: SPOT)",
        "internal_tech_strength": 0.92,
        "conversion_bias": 0.55,
        "competitor":  False,
    },
    {
        "name":        "MLM Constructions and Products",
        "slug":        "mlm-constructions",
        "domain":      "mluisconstruction.com",   # ← correct domain (M Luis Construction)
        "ticker":      None,
        "careers_url": None,
        "news_url":    None,
        "industry":    "Civil Engineering / Construction",
        "domain_display": "Construction & Building Materials",
        "size":        "SMALL",
        "employees":   120,
        "region":      "California, USA (mluisconstruction.com)",
        "internal_tech_strength": 0.25,
        "conversion_bias": 0.70,
        "competitor":  False,
    },
    {
        "name":        "Deenet Services",
        "slug":        "deenet-services",
        "domain":      "deenetservices.net",       # ← correct domain
        "ticker":      None,
        "careers_url": None,
        "news_url":    None,
        "industry":    "IT Services / Digital Solutions",
        "domain_display": "IT Services & Digital Transformation",
        "size":        "SMALL",
        "employees":   80,
        "region":      "India (deenetservices.net)",
        "internal_tech_strength": 0.40,
        "conversion_bias": 0.75,
        "competitor":  False,
    },
    {
        "name":        "Fathima Stores",
        "slug":        "fathima-stores",
        "domain":      "fathimastores.com",
        "ticker":      None,
        "careers_url": None,
        "news_url":    None,
        "industry":    "Retail / Grocery",
        "domain_display": "Retail Supermarket Chain",
        "size":        "SMALL",
        "employees":   200,
        "region":      "Kerala, India",
        "internal_tech_strength": 0.20,
        "conversion_bias": 0.65,
        "competitor":  False,
    },
]


# ── Helpers ────────────────────────────────────────────────────

def estimate_recency(date_str: str) -> int:
    """Convert a published date string to approximate recency_days."""
    if not date_str:
        return 90
    now = datetime.now(timezone.utc)
    for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%B %d, %Y"]:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(1, (now - dt).days)
        except ValueError:
            continue
    return 90


def safe_text(text: str, maxlen: int = 200) -> str:
    """Clean and truncate text."""
    t = re.sub(r"\s+", " ", str(text)).strip()
    return t[:maxlen] if len(t) > maxlen else t


def make_signal(text: str, source: str, recency_days: int,
                verified: bool, verification_source: str = "") -> dict:
    return {
        "text":                safe_text(text),
        "source":              source,
        "recency_days":        recency_days,
        "verified":            verified,
        "verification_source": verification_source,
    }


def extract_tech_signals(tech: dict, company_name: str) -> list[dict]:
    """Convert tech_stack output → infra signals."""
    signals = []
    fw = tech.get("frameworks", [])
    debt = tech.get("debt_signals", {})
    legacy = debt.get("detected_legacy_tech", [])
    score  = debt.get("legacy_score", 0)
    assess = debt.get("assessment", "")

    if fw:
        modern = [f for f in fw if f not in legacy]
        if modern:
            signals.append(make_signal(
                f"{company_name} runs on: {', '.join(modern[:4])}.",
                source=f"Tech stack fingerprint — {tech.get('domain', '')}",
                recency_days=7,
                verified=True,
                verification_source=f"https://{tech.get('domain', '')}",
            ))
    if legacy and score >= 2.5:
        signals.append(make_signal(
            f"Legacy stack detected: {', '.join(legacy[:3])}. {assess}",
            source=f"Tech stack fingerprint — {tech.get('domain', '')}",
            recency_days=7,
            verified=True,
            verification_source=f"https://{tech.get('domain', '')}",
        ))
    return signals


def extract_funding_signals(funding: list[dict]) -> list[dict]:
    signals = []
    for f in funding[:5]:
        headline = f.get("headline", "") or f.get("title", "")
        if not headline or len(headline) < 10:
            continue
        rec = estimate_recency(f.get("date", ""))
        signals.append(make_signal(
            headline,
            source=f.get("source_url", "Google News RSS"),
            recency_days=rec,
            verified=True,
            verification_source=f.get("source_url", ""),
        ))
    return signals


def extract_finance_signals(financials: list[dict], company_name: str) -> list[dict]:
    """Convert Yahoo Finance quarterly statements → 1-2 summary signals."""
    signals = []
    valid = [f for f in financials if f.get("revenue")]
    if not valid:
        return signals
    latest = valid[0]
    rev = latest.get("revenue", 0)
    margin = latest.get("operating_margin")
    quarter = latest.get("quarter", "recent quarter")
    rev_b = rev / 1e9
    text = f"{company_name} reported ${rev_b:.1f}B revenue for {quarter}."
    if margin is not None:
        text += f" Operating margin: {margin:.1%}."
    signals.append(make_signal(
        text,
        source="Yahoo Finance / SEC filings",
        recency_days=45,
        verified=True,
        verification_source=f"https://finance.yahoo.com/quote/{latest.get('ticker','')}/financials",
    ))
    # Revenue trend
    if len(valid) >= 2:
        prev_rev = valid[1].get("revenue", 0)
        if prev_rev and prev_rev > 0:
            change = (rev - prev_rev) / abs(prev_rev)
            direction = "grew" if change > 0 else "declined"
            signals.append(make_signal(
                f"{company_name} revenue {direction} {abs(change):.1%} vs prior quarter (${prev_rev/1e9:.1f}B → ${rev/1e9:.1f}B).",
                source="Yahoo Finance",
                recency_days=45,
                verified=True,
                verification_source=f"https://finance.yahoo.com/quote/{latest.get('ticker','')}/financials",
            ))
    return signals


def extract_press_signals(articles: list[dict]) -> list[dict]:
    """Convert press release articles → product signals."""
    signals = []
    seen = set()
    for a in articles[:6]:
        title = a.get("title", "")
        content = a.get("content", "")
        url = a.get("source_url", "")
        date = a.get("published_date", "")

        if not title or len(title) < 10 or title in seen:
            continue
        seen.add(title)

        text = safe_text(title + (f". {content[:100]}" if content else ""))
        rec = estimate_recency(date)
        # RSS source = company's own feed → verified
        is_rss = "rss" in a.get("_source", "") or "rss" in url
        signals.append(make_signal(
            text,
            source=url or "Google News",
            recency_days=rec,
            verified=bool(url),
            verification_source=url,
        ))
    return signals


def extract_job_signals(jobs: list[dict], company_name: str) -> list[dict]:
    """Summarise job postings into career signals."""
    signals = []
    if not jobs:
        return signals

    # Count depts
    depts = {}
    for j in jobs:
        d = j.get("department", "Other")
        depts[d] = depts.get(d, 0) + 1

    top_depts = sorted(depts.items(), key=lambda x: -x[1])[:3]
    dept_str = ", ".join(f"{d} ({n})" for d, n in top_depts)

    # Keyword extraction
    pivot_kws = set()
    debt_kws  = set()
    for j in jobs[:15]:
        kw = j.get("keywords", {})
        pivot_kws.update(kw.get("pivot", []))
        debt_kws.update(kw.get("tech_debt", []))

    source_type = jobs[0].get("source", "html")
    verified = source_type in ("greenhouse", "lever", "ashby")
    source_label = {"greenhouse": "Greenhouse ATS", "lever": "Lever ATS",
                    "ashby": "Ashby ATS"}.get(source_type, "Careers page HTML")

    text = f"{company_name} has {len(jobs)} open roles — top depts: {dept_str}."
    if pivot_kws:
        text += f" AI/ML keywords in JDs: {', '.join(list(pivot_kws)[:3])}."
    signals.append(make_signal(
        text,
        source=source_label,
        recency_days=14,
        verified=verified,
        verification_source="",
    ))

    # Engineering/tech roles specifically
    eng_jobs = [j for j in jobs if j.get("department") == "Engineering"]
    if eng_jobs:
        titles = [j.get("role_title","")[:50] for j in eng_jobs[:3]]
        signals.append(make_signal(
            f"Engineering hiring: {' | '.join(t for t in titles if t)}.",
            source=source_label,
            recency_days=14,
            verified=verified,
            verification_source="",
        ))

    return signals


def extract_layoff_signals(layoffs: list[dict]) -> list[dict]:
    signals = []
    for l in layoffs[:3]:
        headline = l.get("headline", "")
        if not headline or len(headline) < 10:
            continue
        rec = estimate_recency(l.get("date", ""))
        signals.append(make_signal(
            headline,
            source=l.get("source_url", "Google News"),
            recency_days=rec,
            verified=True,
            verification_source=l.get("source_url", ""),
        ))
    return signals


# ── LLM Intel Generation ──────────────────────────────────────

def _signal_summary(signals: dict, max_signals: int = 6) -> str:
    """Build a concise bullet list of VERIFIED signals for the LLM prompt."""
    lines = []
    count = 0
    for cat, items in signals.items():
        for s in items:
            if count >= max_signals: break
            tag = "✓" if s.get("verified") else "~"
            lines.append(f"  [{tag}] [{cat.upper()}] {s.get('text','')[:120]}")
            count += 1
    return "\n".join(lines) if lines else "  No signals scraped."


def generate_llm_intel(name: str, cfg: dict, signals: dict) -> dict:
    """
    Call the LLM to generate:
      - Decision maker persona (role, pain points, messaging angle)
      - Outreach subject + email body
    Uses ONLY scraped signals as input — no manual data.
    Returns dict with 'llm_persona' and 'llm_outreach' keys.
    Gracefully returns {} in OFFLINE_MODE.
    """
    if OFFLINE_MODE or not llm_call_with_retry:
        return {}

    sig_text = _signal_summary(signals)
    industry = cfg.get("industry", "")
    size     = cfg.get("size", "")
    region   = cfg.get("region", "")
    employees = cfg.get("employees", "")

    print(f"  [LLM] Generating persona for {name}...")
    try:
        persona_result = llm_call_with_retry(
            prompt=(
                f"Company: {name}\n"
                f"Industry: {industry}\n"
                f"Size: {size} ({employees} employees), Region: {region}\n"
                f"Scraped signals:\n{sig_text}\n\n"
                "Who is the ideal B2B decision maker to contact at this company? "
                "Base the persona entirely on the signals above."
            ),
            system=(
                "You are a B2B sales intelligence analyst. "
                "Return ONLY JSON with these keys: "
                '"role" (string), "pain_points" (array of 3 strings), '
                '"messaging_angle" (1 sentence), "why_now" (1 sentence).'
            ),
        )
        print(f"  [LLM] Persona generated: {persona_result.get('role','?')}")
    except Exception as e:
        print(f"  [LLM] Persona generation failed: {e}")
        persona_result = {}

    print(f"  [LLM] Generating outreach for {name}...")
    try:
        role = persona_result.get("role", "CTO / Technical Leader")
        angle = persona_result.get("messaging_angle", "")
        outreach_result = llm_call_with_retry(
            prompt=(
                f"Company: {name} ({industry}, {region})\n"
                f"Target persona: {role}\n"
                f"Messaging angle: {angle}\n"
                f"Scraped signals (data source — do NOT invent anything):\n{sig_text}\n\n"
                "Write a short, specific, non-generic cold outreach email and LinkedIn DM "
                "grounded only in the signals above. Reference specific facts."
            ),
            system=(
                "You are a senior B2B sales strategist. "
                "Return ONLY JSON with keys: "
                '"subject" (email subject line), '
                '"email" (3-4 paragraph email body, no em dashes), '
                '"linkedin_dm" (2-3 sentence LinkedIn message).'
            ),
        )
        print(f"  [LLM] Outreach generated: subject=\"{outreach_result.get('subject','?')}\"")
    except Exception as e:
        print(f"  [LLM] Outreach generation failed: {e}")
        outreach_result = {}

    return {
        "llm_persona":  persona_result,
        "llm_outreach": outreach_result,
    }


# ── Main ───────────────────────────────────────────────────────

def scrape_company(cfg: dict) -> dict:
    name    = cfg["name"]
    domain  = cfg["domain"]
    ticker  = cfg.get("ticker")
    careers = cfg.get("careers_url")
    news_pg = cfg.get("news_url")

    print(f"\n{'='*55}")
    print(f"Scraping: {name}")
    print(f"{'='*55}")

    signals  = {"funding": [], "careers": [], "product": [], "infra": []}
    dm_list  = []

    # 1. Tech stack (always, any company with a domain)
    print(f"  [1/5] Tech stack → {domain}")
    try:
        tech = detect_tech_stack(domain, name)
        infra_from_tech = extract_tech_signals(tech, name)
        signals["infra"].extend(infra_from_tech)
        print(f"        → {len(tech.get('frameworks', []))} frameworks, "
              f"{len(tech.get('debt_signals', {}).get('detected_legacy_tech', []))} legacy")
    except Exception as e:
        print(f"        ✗ Tech stack failed: {e}")

    # 2. Press releases (Google News RSS always kicks in as fallback)
    print(f"  [2/5] Press releases → {name}")
    try:
        articles = scrape_press_releases(name, domain, news_page_url=news_pg, limit=10)
        prod_signals = extract_press_signals(articles)
        signals["product"].extend(prod_signals)
        print(f"        → {len(articles)} articles, {len(prod_signals)} signals")
    except Exception as e:
        print(f"        ✗ Press releases failed: {e}")

    # 3. Funding news (Google News RSS — works for any company by name)
    print(f"  [3/5] Funding news → {name}")
    try:
        funding = scrape_funding_news(name)
        fund_signals = extract_funding_signals(funding)
        signals["funding"].extend(fund_signals)
        print(f"        → {len(funding)} rounds, {len(fund_signals)} signals")
    except Exception as e:
        print(f"        ✗ Funding news failed: {e}")

    # 4. Yahoo Finance — only for public companies with ticker
    if ticker:
        print(f"  [4/5] Yahoo Finance → {ticker}")
        try:
            financials = scrape_yahoo_finance(ticker, name)
            fin_signals = extract_finance_signals(financials, name)
            signals["funding"].extend(fin_signals)
            print(f"        → {len(financials)} statements, {len(fin_signals)} signals")
        except Exception as e:
            print(f"        ✗ Yahoo Finance failed: {e}")
    else:
        print(f"  [4/5] Yahoo Finance → SKIPPED (no ticker)")

    # 5. Jobs / careers — only if URL provided
    if careers and HAS_JOBS:
        print(f"  [5/5] Careers → {careers}")
        try:
            jobs = scrape_careers_page(careers, name, limit=25)
            job_signals = extract_job_signals(jobs, name)
            signals["careers"].extend(job_signals)
            print(f"        → {len(jobs)} jobs, {len(job_signals)} signals")
            # Try to extract DM from engineering leadership
            if jobs:
                dm_list.append({
                    "name":    "",
                    "role":    "CTO / VP Engineering",
                    "source":  "inferred from careers",
                })
        except Exception as e:
            print(f"        ✗ Careers scrape failed: {e}")
    else:
        print(f"  [5/5] Careers → SKIPPED (no URL configured)")

    # 6. Layoff risk signals
    print(f"  [+] Layoff check → {name}")
    try:
        layoffs = scrape_layoff_news(name, domain)
        layoff_sigs = extract_layoff_signals(layoffs)
        signals["infra"].extend(layoff_sigs)  # Layoffs = infra/risk signal
        print(f"        → {len(layoffs)} layoff events")
    except Exception as e:
        print(f"        ✗ Layoff check failed: {e}")

    # Remove empty categories
    signals = {k: v for k, v in signals.items() if v}

    total = sum(len(v) for v in signals.values())
    verified = sum(1 for v in signals.values() for s in v if s.get("verified"))
    print(f"\n  ✓ Done: {total} signals ({verified} verified, {total - verified} unverified)")

    return {
        "meta": {
            "industry":    cfg["industry"],
            "size":        cfg["size"],
            "region":      cfg["region"],
            "employees":   cfg["employees"],
            "competitor":  cfg["competitor"],
            "competitor_note": "",
            "internal_tech_strength": cfg["internal_tech_strength"],
            "conversion_bias": cfg["conversion_bias"],
            "domain_display": cfg["domain_display"],
        },
        "signals":          signals,
        "decision_makers":  dm_list or [{"name": "", "role": "CTO / Head of Technology"}],
    }


def main():
    # Load existing cache
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)
    else:
        cache = {}

    for cfg in COMPANIES:
        name = cfg["name"]
        try:
            result = scrape_company(cfg)

            # ── LLM enrichment (uses scraped signals only) ────
            llm_intel = generate_llm_intel(name, cfg, result.get("signals", {}))
            if llm_intel:
                result.update(llm_intel)  # adds 'llm_persona' and 'llm_outreach'

            cache[name] = result
        except Exception as e:
            print(f"\n\u2717 FATAL error scraping {name}: {e}")
            import traceback; traceback.print_exc()

    # Save cache
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)

    print(f"\n\n{'='*55}")
    print(f"\u2705 search_cache.json updated \u2014 {len(COMPANIES)} companies scraped")
    if not OFFLINE_MODE:
        print(f"   LLM persona + outreach generated for all companies")
    else:
        print(f"   LLM SKIPPED (set BYTEZ_API_KEY or OPENAI_API_KEY in .env to enable)")
    print(f"   Next: python seed_db.py")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
