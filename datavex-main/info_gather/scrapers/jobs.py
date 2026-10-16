"""
Job Postings Scraper
Sources:
  1. Company's own careers page (safest, no ToS issues)
  2. Common ATS platforms (Greenhouse, Lever, Workday, Ashby)
Extracts: role title, department, description, strategic keywords
"""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from loguru import logger
from utils.http import safe_get, get_session


# ATS-specific job listing endpoints
ATS_PATTERNS = {
    "greenhouse": "https://boards.greenhouse.io/{slug}/jobs",
    "lever":      "https://jobs.lever.co/{slug}",
    "ashby":      "https://jobs.ashbyhq.com/{slug}",
}

# Keywords that signal strategic changes
PIVOT_KEYWORDS     = ["AI", "machine learning", "generative", "LLM", "NLP", "data platform",
                      "cloud native", "SaaS", "enterprise", "platform engineering", "MLOps"]
TECH_DEBT_KEYWORDS = ["legacy", "migration", "moderniz", "refactor", "monolith", "microservice",
                      "cloud migration", "re-architect", "technical debt", "ETL", "pipeline"]
FISCAL_KEYWORDS    = ["cost reduction", "efficiency", "headcount", "lean", "profitable",
                      "streamline", "optimization", "runway", "burn rate"]


def scrape_careers_page(careers_url: str, company_name: str, limit: int = 30) -> list[dict]:
    """
    Attempt to scrape job listings from a careers page.
    Tries direct HTML parsing; falls back to known ATS endpoints.
    Returns list of job dicts.
    """
    session = get_session()
    jobs = []

    # Try direct page scrape first
    jobs = _scrape_html_careers(careers_url, company_name, session, limit)

    # If nothing found, try common ATS patterns
    if not jobs:
        slug = _guess_ats_slug(careers_url)
        for ats, template in ATS_PATTERNS.items():
            ats_url = template.format(slug=slug)
            try:
                jobs = _scrape_html_careers(ats_url, company_name, session, limit)
                if jobs:
                    logger.info(f"[{company_name}] Jobs found via {ats} ATS")
                    break
            except Exception:
                continue

    logger.info(f"[{company_name}] Scraped {len(jobs)} job postings")
    return jobs


def _scrape_html_careers(url: str, company_name: str, session, limit: int) -> list[dict]:
    jobs = []
    try:
        resp = safe_get(url, session)
        soup = BeautifulSoup(resp.text, "lxml")

        # Generic heuristic: find all links that look like job postings
        job_links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if _looks_like_job_link(text, href):
                full_url = urljoin(url, href)
                job_links.append((text, full_url))

        # Deduplicate
        seen = set()
        unique_links = []
        for t, u in job_links:
            if u not in seen:
                seen.add(u)
                unique_links.append((t, u))

        for title, job_url in unique_links[:limit]:
            job = _scrape_job_detail(title, job_url, company_name, session)
            if job:
                jobs.append(job)

    except Exception as e:
        logger.debug(f"Careers page scrape failed ({url}): {e}")

    return jobs


def _scrape_job_detail(title: str, url: str, company_name: str, session) -> dict | None:
    try:
        resp = safe_get(url, session)
        soup = BeautifulSoup(resp.text, "lxml")

        # Remove nav/footer noise
        for tag in soup.select("nav, footer, header, script, style"):
            tag.decompose()

        description = soup.get_text(separator=" ", strip=True)[:5000]
        keywords = _extract_keywords(title + " " + description)

        return {
            "company_name": company_name,
            "role_title":   title[:255],
            "department":   _guess_department(title),
            "description":  description,
            "keywords":     keywords,
            "posted_date":  _extract_date(description),
            "source":       _guess_ats_from_url(url),
        }
    except Exception as e:
        logger.debug(f"Job detail failed ({url}): {e}")
        return None


def _looks_like_job_link(text: str, href: str) -> bool:
    job_terms = r"(engineer|developer|manager|analyst|scientist|architect|designer|" \
                r"sales|marketing|devops|sre|director|head of|vp |lead |senior |staff )"
    url_terms  = r"(jobs|careers|openings|positions|apply|role|job)"
    return bool(
        re.search(job_terms, text, re.I) or
        re.search(url_terms, href, re.I)
    ) and len(text) > 3


def _extract_keywords(text: str) -> dict:
    text_lower = text.lower()
    return {
        "pivot":     [kw for kw in PIVOT_KEYWORDS     if kw.lower() in text_lower],
        "tech_debt": [kw for kw in TECH_DEBT_KEYWORDS if kw.lower() in text_lower],
        "fiscal":    [kw for kw in FISCAL_KEYWORDS    if kw.lower() in text_lower],
    }


def _guess_department(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["engineer", "developer", "sre", "devops", "architect", "data"]): return "Engineering"
    if any(x in t for x in ["sales", "account", "revenue", "business dev"]): return "Sales"
    if any(x in t for x in ["market", "growth", "brand", "demand"]): return "Marketing"
    if any(x in t for x in ["product", "pm ", "program"]): return "Product"
    if any(x in t for x in ["finance", "accounting", "fp&a"]): return "Finance"
    if any(x in t for x in ["hr", "people", "talent", "recruit"]): return "HR"
    return "Other"


def _guess_ats_slug(url: str) -> str:
    """Extract company slug from URL path."""
    parts = url.rstrip("/").split("/")
    return parts[-1] if parts else "unknown"


def _guess_ats_from_url(url: str) -> str:
    for ats in ATS_PATTERNS:
        if ats in url:
            return ats
    return "careers_page"


def _extract_date(text: str) -> str:
    match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*.{0,5}20\d{2}", text)
    return match.group(0) if match else ""
