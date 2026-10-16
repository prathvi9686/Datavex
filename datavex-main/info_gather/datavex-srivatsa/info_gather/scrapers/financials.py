"""
Financials Scraper
  - Yahoo Finance for public companies
  - Google News RSS for layoffs + funding (company-specific only)
"""
import re
import feedparser
from loguru import logger
from utils.http import safe_get, get_session

YAHOO_SUMMARY_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=incomeStatementHistory,cashflowStatementHistory,financialData,defaultKeyStatistics"

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# Terms that indicate the headline is about a VC firm, not the company
VC_FIRM_PATTERNS = [
    r"notion capital",
    r"notion ventures",
    r"notion fund",
]

# Terms that indicate a headline is about REVENUE not a funding round
REVENUE_INDICATORS = [
    "annual revenue", "arr", "monthly revenue", "revenue run rate",
    "in revenue", "revenue hits", "revenue reaches", "revenue milestone",
    "revenue growth", "annual recurring",
]


def scrape_yahoo_finance(ticker: str, company_name: str) -> list[dict]:
    session = get_session()
    results = []
    try:
        resp = safe_get(YAHOO_SUMMARY_URL.format(ticker=ticker), session, timeout=15)
        data = resp.json().get("quoteSummary", {}).get("result", [{}])[0]
        income = data.get("incomeStatementHistory", {}).get("incomeStatementHistory", [])
        for stmt in income[:8]:
            def _val(k): return stmt.get(k, {}).get("raw")
            rev = _val("totalRevenue")
            ni  = _val("netIncome")
            gp  = _val("grossProfit")
            results.append({
                "company_name":     company_name,
                "ticker":           ticker,
                "quarter":          stmt.get("endDate", {}).get("fmt", ""),
                "revenue":          rev,
                "gross_profit":     gp,
                "net_income":       ni,
                "operating_margin": round(ni / rev, 4) if rev and ni else None,
                "gross_margin":     round(gp / rev, 4) if rev and gp else None,
                "source":           "yahoo_finance",
            })
        logger.info(f"[{company_name}] Yahoo Finance: {len(results)} statements")
    except Exception as e:
        logger.warning(f"[{company_name}] Yahoo Finance failed: {e}")
    return results


def scrape_layoff_news(company_name: str, domain: str = "") -> list[dict]:
    results = []
    queries = [
        f'"{company_name}" layoffs',
        f'"{company_name}" job cuts',
        f'"{company_name}" workforce reduction',
    ]
    LAYOFF_TERMS = [
        "layoff", "lay off", "laid off", "job cut", "workforce reduction",
        "headcount reduction", "restructur", "redundanc", "retrench",
        "downsize", "fired", "let go", "eliminated position",
    ]
    seen = set()

    for query in queries:
        url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                title = entry.get("title", "")
                link  = entry.get("link", "")
                if link in seen:
                    continue
                if company_name.lower() not in title.lower():
                    continue
                if not any(t in title.lower() for t in LAYOFF_TERMS):
                    continue
                if _is_vc_firm_news(title):
                    continue
                seen.add(link)
                results.append({
                    "company_name": company_name,
                    "date":         entry.get("published", ""),
                    "headcount":    _extract_headcount(title),
                    "percentage":   _extract_percentage(title),
                    "source_url":   link,
                    "headline":     title,
                })
        except Exception as e:
            logger.debug(f"Layoff news failed: {e}")
    logger.info(f"[{company_name}] Layoff signals: {len(results)} found")
    return results


def scrape_funding_news(company_name: str) -> list[dict]:
    results = []
    queries = [
        f'"{company_name}" raises funding',
        f'"{company_name}" series valuation',
        f'"{company_name}" IPO tender offer',
        f'"{company_name}" investment round',
    ]
    FUNDING_TERMS = [
        "raises", "raised", "funding", "series a", "series b", "series c",
        "seed round", "valuation", "ipo", "tender offer", "investment",
        "venture", "million", "billion",
    ]
    seen = set()
    for query in queries:
        url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                title = entry.get("title", "")
                link  = entry.get("link", "")
                if link in seen:
                    continue
                if company_name.lower() not in title.lower():
                    continue
                title_lower = title.lower()
                if not any(t in title_lower for t in FUNDING_TERMS):
                    continue
                # Skip VC firm news
                if _is_vc_firm_news(title):
                    logger.debug(f"Skipping VC firm news: {title}")
                    continue
                # Skip revenue articles misread as funding
                if _is_revenue_not_funding(title):
                    logger.debug(f"Skipping revenue article: {title}")
                    continue
                # Extract amount — but only if this isn't a revenue article
                amount = _extract_amount(title)
                seen.add(link)
                results.append({
                    "company_name": company_name,
                    "round_type":   _extract_round_type(title),
                    "amount_usd":   amount,
                    "date":         entry.get("published", ""),
                    "investors":    [],
                    "source_url":   link,
                    "headline":     title,
                })
        except Exception as e:
            logger.debug(f"Funding news failed: {e}")
    logger.info(f"[{company_name}] Funding signals: {len(results)} found")
    return results


def compute_fiscal_pressure(
    financials: list[dict],
    layoffs: list[dict],
    funding: list[dict],
) -> dict:
    score, signals = 0, []

    if len(financials) >= 2:
        rev = [f.get("revenue") for f in financials if f.get("revenue")]
        if len(rev) >= 2:
            change = (rev[0] - rev[1]) / abs(rev[1]) if rev[1] else 0
            if change < -0.05:
                score += 3
                signals.append(f"Revenue declining {change:.1%} QoQ")
            elif change < 0:
                score += 1
                signals.append(f"Revenue slightly down {change:.1%} QoQ")
        margins = [f.get("operating_margin") for f in financials if f.get("operating_margin")]
        if len(margins) >= 2 and margins[0] < margins[1]:
            score += 2
            signals.append(f"Margin compression: {margins[0]:.1%} vs {margins[1]:.1%}")

    if layoffs:
        score += min(4, len(layoffs) * 2)
        signals.append(f"{len(layoffs)} layoff event(s): {[l['headline'][:60] for l in layoffs[:2]]}")

    # Large recent funding reduces pressure (but floor at 1 if layoffs exist)
    if funding:
        large_rounds = [f for f in funding if f.get("amount_usd") and f["amount_usd"] > 50_000_000]
        if large_rounds:
            reduction = 1
            score = max(0 if not layoffs else 1, score - reduction)
            signals.append(f"Recent funding: {large_rounds[0]['headline'][:60]}")

    score = min(10, score)
    label = ("Critical" if score >= 8 else "High" if score >= 6 else
             "Medium" if score >= 4 else "Low" if score >= 2 else "Minimal")
    return {"fiscal_pressure_score": score, "fiscal_pressure_label": label, "signals": signals}


def _is_vc_firm_news(title: str) -> bool:
    t = title.lower()
    return any(re.search(p, t) for p in VC_FIRM_PATTERNS)


def _is_revenue_not_funding(title: str) -> bool:
    """Return True if the headline is about revenue, not a funding round."""
    t = title.lower()
    return any(indicator in t for indicator in REVENUE_INDICATORS)


def _extract_headcount(text: str) -> int | None:
    m = re.search(r"(\d[\d,]+)\s*(employee|worker|staff|job|position|role)", text, re.I)
    return int(m.group(1).replace(",", "")) if m else None


def _extract_percentage(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    return float(m.group(1)) if m else None


def _extract_amount(text: str) -> float | None:
    # Only extract if NOT a revenue article (already checked upstream)
    m = re.search(r"\$(\d+(?:\.\d+)?)\s*(million|billion|M|B)\b", text, re.I)
    if m:
        amount = float(m.group(1))
        unit   = m.group(2).lower()
        return amount * 1_000_000_000 if unit in ("billion", "b") else amount * 1_000_000
    return None


def _extract_round_type(text: str) -> str:
    t = text.lower()
    if "series a" in t: return "Series A"
    if "series b" in t: return "Series B"
    if "series c" in t: return "Series C"
    if "series d" in t: return "Series D"
    if "seed"     in t: return "Seed"
    if "ipo"      in t: return "IPO"
    if "tender"   in t: return "Tender Offer"
    if "growth"   in t: return "Growth"
    if "venture"  in t: return "Venture"
    return "Unknown"
