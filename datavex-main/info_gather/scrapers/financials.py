"""
Financial Data Scraper
Sources:
  1. Yahoo Finance - revenue trends, margins (free, no API key)
  2. Layoffs.fyi - layoff events (free)
  3. Crunchbase basic page scrape - funding rounds (free limited)
  4. Google News RSS - layoff/funding news
"""
import re
import json
import feedparser
from loguru import logger
from utils.http import safe_get, get_session

YAHOO_FINANCE_SUMMARY = "https://finance.yahoo.com/quote/{ticker}"
YAHOO_FINANCE_INCOME  = "https://finance.yahoo.com/quote/{ticker}/financials"
LAYOFFS_FYI           = "https://layoffs.fyi"
GOOGLE_NEWS_RSS       = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


# ─── Revenue / Margin Scraping ───────────────────────────────────────────────

def scrape_yahoo_finance(ticker: str, company_name: str) -> list[dict]:
    """
    Scrape quarterly financial data from Yahoo Finance.
    Returns list of dicts per available quarter.
    """
    quarters = []
    session  = get_session()
    url = YAHOO_FINANCE_INCOME.format(ticker=ticker.upper())

    try:
        resp = safe_get(url, session, timeout=20)

        # Yahoo Finance embeds data in a JSON blob in the page
        match = re.search(r'root\.App\.main\s*=\s*(\{.+?\});\n', resp.text, re.S)
        if not match:
            match = re.search(r'"QuarterlyIncomeStatementHistory":\{"incomeStatementHistory":(\[.+?\])', resp.text)

        if match:
            try:
                data = json.loads(match.group(1))
                quarters = _parse_yahoo_income(data, company_name, ticker)
            except json.JSONDecodeError:
                pass

        # Fallback: scrape visible table numbers
        if not quarters:
            quarters = _scrape_yahoo_table(resp.text, company_name, ticker)

        logger.info(f"[{company_name}] Yahoo Finance: {len(quarters)} quarters")

    except Exception as e:
        logger.warning(f"Yahoo Finance scrape failed ({ticker}): {e}")

    return quarters


def _parse_yahoo_income(data: dict, company_name: str, ticker: str) -> list[dict]:
    """Try to extract quarterly income data from Yahoo Finance JSON blob."""
    results = []
    try:
        store = data.get("context", {}).get("dispatcher", {}).get("stores", {})
        qs_data = (
            store.get("QuoteSummaryStore", {})
                 .get("incomeStatementHistoryQuarterly", {})
                 .get("incomeStatementHistory", [])
        )
        for q in qs_data:
            results.append({
                "company_name":     company_name,
                "ticker":           ticker,
                "quarter":          q.get("endDate", {}).get("fmt", ""),
                "revenue":          q.get("totalRevenue", {}).get("raw", None),
                "net_income":       q.get("netIncome", {}).get("raw", None),
                "gross_profit":     q.get("grossProfit", {}).get("raw", None),
                "operating_income": q.get("operatingIncome", {}).get("raw", None),
                "operating_margin": None,   # computed below
                "gross_margin":     None,
                "source":           "yahoo_finance",
            })
            # Compute margins
            if results[-1]["revenue"] and results[-1]["operating_income"]:
                results[-1]["operating_margin"] = round(
                    results[-1]["operating_income"] / results[-1]["revenue"] * 100, 2
                )
            if results[-1]["revenue"] and results[-1]["gross_profit"]:
                results[-1]["gross_margin"] = round(
                    results[-1]["gross_profit"] / results[-1]["revenue"] * 100, 2
                )
    except Exception as e:
        logger.debug(f"Yahoo JSON parse failed: {e}")
    return results


def _scrape_yahoo_table(html: str, company_name: str, ticker: str) -> list[dict]:
    """Regex fallback to pull raw numbers from Yahoo Finance table."""
    numbers = re.findall(r'([\d,]+(?:\.\d+)?[BMK]?)\s*(?:TTM|Q[1-4]\s*20\d{2})', html)
    if numbers:
        logger.debug(f"Fallback table scrape found {len(numbers)} values for {ticker}")
    return []   # stub — in full version parse table rows


# ─── Layoff Events ───────────────────────────────────────────────────────────

def scrape_layoff_news(company_name: str) -> list[dict]:
    """
    Search Google News RSS for layoff events for a company.
    Also checks layoffs.fyi via Google News.
    """
    layoffs = []
    queries = [
        f"{company_name} layoffs 2024",
        f"{company_name} layoffs 2025",
        f"{company_name} headcount reduction",
        f"{company_name} job cuts",
    ]

    for query in queries:
        url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                layoff = _parse_layoff_entry(entry, company_name)
                if layoff:
                    layoffs.append(layoff)
        except Exception as e:
            logger.debug(f"News RSS failed for '{query}': {e}")

    # Deduplicate by title
    seen = set()
    unique = []
    for l in layoffs:
        if l["source_url"] not in seen:
            seen.add(l["source_url"])
            unique.append(l)

    logger.info(f"[{company_name}] Layoff signals: {len(unique)} found")
    return unique


def _parse_layoff_entry(entry, company_name: str) -> dict | None:
    """Extract layoff details from a news RSS entry."""
    title    = entry.get("title", "")
    url      = entry.get("link", "")
    date     = entry.get("published", "")
    summary  = entry.get("summary", "")

    # Verify it's actually about layoffs
    layoff_terms = r"(layoff|laid.off|job.cut|headcount|redundanc|retrench|workforce.reduc)"
    if not re.search(layoff_terms, title + summary, re.I):
        return None

    # Try to extract headcount from title
    headcount_match = re.search(r"(\d[\d,]+)\s*(employee|worker|staff|job)", title + summary, re.I)
    headcount = int(headcount_match.group(1).replace(",", "")) if headcount_match else None

    pct_match = re.search(r"(\d+)\s*%", title + summary)
    percentage = float(pct_match.group(1)) if pct_match else None

    return {
        "company_name": company_name,
        "date":         date,
        "headcount":    headcount,
        "percentage":   percentage,
        "source_url":   url,
        "headline":     title,
    }


# ─── Funding Rounds ──────────────────────────────────────────────────────────

def scrape_funding_news(company_name: str) -> list[dict]:
    """
    Search Google News RSS for funding round announcements.
    Free alternative to Crunchbase API.
    """
    rounds = []
    queries = [
        f"{company_name} funding round 2024",
        f"{company_name} series funding raised",
        f"{company_name} raises million investment",
    ]

    for query in queries:
        url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                rd = _parse_funding_entry(entry, company_name)
                if rd:
                    rounds.append(rd)
        except Exception as e:
            logger.debug(f"Funding RSS failed: {e}")

    # Deduplicate
    seen, unique = set(), []
    for r in rounds:
        if r["source_url"] not in seen:
            seen.add(r["source_url"])
            unique.append(r)

    logger.info(f"[{company_name}] Funding signals: {len(unique)} found")
    return unique


def _parse_funding_entry(entry, company_name: str) -> dict | None:
    title   = entry.get("title", "")
    url     = entry.get("link", "")
    date    = entry.get("published", "")
    summary = entry.get("summary", "")

    funding_terms = r"(series [a-f]|seed round|raise[sd]|funding|invest|valuation|pre-seed)"
    if not re.search(funding_terms, title + summary, re.I):
        return None

    # Round type
    round_match = re.search(
        r"(seed|series [a-f]|pre-seed|growth|late.stage|ipo|spac)",
        title + summary, re.I
    )
    round_type = round_match.group(0).title() if round_match else "Unknown"

    # Amount
    amount_match = re.search(
        r"\$\s*([\d.]+)\s*(million|billion|M|B)\b",
        title + summary, re.I
    )
    amount_usd = None
    if amount_match:
        num = float(amount_match.group(1))
        unit = amount_match.group(2).lower()
        amount_usd = num * 1_000_000_000 if "b" in unit else num * 1_000_000

    return {
        "company_name": company_name,
        "round_type":   round_type,
        "amount_usd":   amount_usd,
        "date":         date,
        "investors":    [],    # would need deeper scrape
        "source_url":   url,
        "headline":     title,
    }


# ─── Fiscal Pressure Composite ───────────────────────────────────────────────

def compute_fiscal_pressure(
    financials: list[dict],
    layoffs: list[dict],
    funding_rounds: list[dict],
) -> dict:
    """
    Compute a composite fiscal pressure score (0-10) from all financial signals.
    """
    score  = 0
    signals = []

    # Revenue trend: are last 2 quarters declining?
    if len(financials) >= 2:
        rev_vals = [f["revenue"] for f in financials if f.get("revenue")]
        if len(rev_vals) >= 2 and rev_vals[0] < rev_vals[1]:
            score += 2
            signals.append("Revenue declining QoQ")

    # Margin compression
    margins = [f["operating_margin"] for f in financials if f.get("operating_margin")]
    if len(margins) >= 2:
        margin_delta = margins[0] - margins[-1]
        if margin_delta < -2:
            score += 2
            signals.append(f"Operating margin down {abs(margin_delta):.1f}pp")
        elif margin_delta < -1:
            score += 1
            signals.append("Slight margin compression")

    # Recent layoffs
    if layoffs:
        score += min(3, len(layoffs))
        signals.append(f"{len(layoffs)} layoff event(s) detected")

    # Funding runway pressure
    if funding_rounds:
        latest = funding_rounds[0]
        # Estimate months since last round
        import re, datetime
        date_str = latest.get("date", "")
        year_match = re.search(r"20\d{2}", date_str)
        if year_match:
            approx_year = int(year_match.group(0))
            months_ago = (datetime.datetime.now().year - approx_year) * 12
            if months_ago > 18:
                score += 2
                signals.append(f"Last funding ~{months_ago}m ago — runway pressure")
            elif months_ago > 12:
                score += 1

    score = min(10, score)
    label = (
        "Critical" if score >= 8 else
        "High"     if score >= 6 else
        "Medium"   if score >= 4 else
        "Low"      if score >= 2 else
        "Minimal"
    )

    return {
        "fiscal_pressure_score": score,
        "fiscal_pressure_label": label,
        "signals": signals,
    }
