"""
Job Postings Scraper — ATS JSON APIs first, HTML last resort.
Uses quick_get (no retry) for ATS probing so slug misses fail instantly.
"""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from loguru import logger
from utils.http import safe_get, quick_get, get_session

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
LEVER_API      = "https://api.lever.co/v0/postings/{slug}?mode=json"
ASHBY_API      = "https://api.ashbyhq.com/posting-api/job-board/{slug}"

PIVOT_KEYWORDS = [
    "AI", "artificial intelligence", "machine learning", "generative", "LLM",
    "large language model", "NLP", "data platform", "cloud native", "SaaS",
    "enterprise", "platform engineering", "MLOps", "foundation model",
    "vector database", "RAG", "agentic",
]
TECH_DEBT_KEYWORDS = [
    "legacy", "migration", "moderniz", "refactor", "monolith", "microservice",
    "cloud migration", "re-architect", "technical debt", "ETL", "pipeline",
    "rewrite", "decomposition",
]
FISCAL_KEYWORDS = [
    "cost reduction", "efficiency", "headcount", "lean", "profitable",
    "streamline", "optimization", "runway", "burn rate", "budget",
]


def scrape_careers_page(careers_url: str, company_name: str, limit: int = 30) -> list[dict]:
    slugs   = _generate_slugs(careers_url, company_name)
    session = get_session()

    logger.debug(f"[{company_name}] Trying slugs: {slugs}")

    for slug in slugs:
        jobs = _try_greenhouse(slug, company_name, session, limit)
        if jobs:
            logger.info(f"[{company_name}] Greenhouse ({slug}) → {len(jobs)} jobs")
            return jobs

    for slug in slugs:
        jobs = _try_lever(slug, company_name, session, limit)
        if jobs:
            logger.info(f"[{company_name}] Lever ({slug}) → {len(jobs)} jobs")
            return jobs

    for slug in slugs:
        jobs = _try_ashby(slug, company_name, session, limit)
        if jobs:
            logger.info(f"[{company_name}] Ashby ({slug}) → {len(jobs)} jobs")
            return jobs

    jobs = _scrape_html_careers(careers_url, company_name, session, limit)
    if jobs:
        logger.info(f"[{company_name}] HTML fallback → {len(jobs)} jobs")
        return jobs

    logger.warning(f"[{company_name}] No jobs found from any source")
    return []


def _generate_slugs(careers_url: str, company_name: str) -> list[str]:
    slugs = []

    for pattern in [
        r"greenhouse\.io/([^/\?#]+)",
        r"lever\.co/([^/\?#]+)",
        r"ashbyhq\.com/([^/\?#]+)",
    ]:
        m = re.search(pattern, careers_url, re.I)
        if m:
            slugs.append(m.group(1).lower())

    clean = re.sub(r"[^a-z0-9\s]", "", company_name.lower()).strip()
    words = clean.split()
    slugs += [
        "".join(words),
        "-".join(words),
        words[0] if words else "",
    ]

    m = re.search(r"https?://(?:www\.|jobs\.)?([^/\.]+)", careers_url)
    if m:
        slugs.append(m.group(1).lower())

    seen, out = set(), []
    for s in slugs:
        if s and s not in seen:

            seen.add(s)
            out.append(s)
    return out


# ── Greenhouse ────────────────────────────────────────────────────────────────

def _try_greenhouse(slug: str, company_name: str, session, limit: int) -> list[dict]:
    try:
        resp = quick_get(GREENHOUSE_API.format(slug=slug), session)
        jobs = resp.json().get("jobs", [])
        if not jobs:
            return []
        return [_parse_greenhouse(j, company_name) for j in jobs[:limit]]
    except Exception as e:
        logger.debug(f"Greenhouse '{slug}': {type(e).__name__}")
        return []

def _parse_greenhouse(j: dict, company_name: str) -> dict:
    title   = j.get("title", "")
    content = BeautifulSoup(j.get("content", "") or "", "lxml").get_text(" ", strip=True)[:3000]
    dept    = (j.get("departments") or [{}])[0].get("name", "") or _dept(title)
    loc     = (j.get("offices") or [{}])[0].get("name", "")
    return _job(company_name, title, dept, content, loc, "greenhouse")


# ── Lever ─────────────────────────────────────────────────────────────────────

def _try_lever(slug: str, company_name: str, session, limit: int) -> list[dict]:
    try:
        resp = quick_get(LEVER_API.format(slug=slug), session)
        jobs = resp.json()
        if not isinstance(jobs, list) or not jobs:
            return []
        return [_parse_lever(j, company_name) for j in jobs[:limit]]
    except Exception as e:
        logger.debug(f"Lever '{slug}': {type(e).__name__}")
        return []

def _parse_lever(j: dict, company_name: str) -> dict:
    title = j.get("text", "")
    dept  = j.get("categories", {}).get("team", "") or _dept(title)
    loc   = j.get("categories", {}).get("location", "")
    desc  = j.get("descriptionPlain", "") or BeautifulSoup(
        j.get("description", ""), "lxml").get_text(" ", strip=True)
    return _job(company_name, title, dept, desc[:3000], loc, "lever")


# ── Ashby ─────────────────────────────────────────────────────────────────────

def _try_ashby(slug: str, company_name: str, session, limit: int) -> list[dict]:
    try:
        resp = quick_get(ASHBY_API.format(slug=slug), session)
        data = resp.json()
        # Ashby API has two possible response shapes
        jobs = (
            data.get("jobPostings") or
            data.get("results") or
            data.get("jobs") or
            []
        )
        logger.debug(f"Ashby '{slug}' response keys: {list(data.keys())} | jobs found: {len(jobs)}")
        if not jobs:
            return []
        return [_parse_ashby(j, company_name) for j in jobs[:limit]]
    except Exception as e:
        logger.debug(f"Ashby '{slug}': {type(e).__name__}: {e}")
        return []

def _parse_ashby(j: dict, company_name: str) -> dict:
    title = j.get("title", "")
    dept  = j.get("department", "") or j.get("departmentName", "") or _dept(title)
    loc   = j.get("locationName", "") or j.get("location", "")
    desc  = BeautifulSoup(
        j.get("descriptionHtml", "") or j.get("description", "") or j.get("descriptionSafe", "") or "",
        "lxml").get_text(" ", strip=True)[:3000]
    return _job(company_name, title, dept, desc, loc, "ashby")


# ── HTML fallback ─────────────────────────────────────────────────────────────

def _scrape_html_careers(url: str, company_name: str, session, limit: int) -> list[dict]:
    jobs = []
    try:
        resp = safe_get(url, session, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        if len(soup.get_text(strip=True)) < 500:
            logger.debug(f"[{company_name}] SPA detected — HTML scrape skipped")
            return []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            full = urljoin(url, href)
            if _href_is_job(href) and _title_is_job(text) and full not in seen:
                seen.add(full)
                j = _scrape_detail(text, full, company_name, session)
                if j:
                    jobs.append(j)
            if len(jobs) >= limit:
                break
    except Exception as e:
        logger.debug(f"HTML careers failed: {e}")
    return jobs

def _scrape_detail(title: str, url: str, company_name: str, session) -> dict | None:
    try:
        resp = safe_get(url, session, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup.select("nav,footer,header,script,style,aside"):
            tag.decompose()
        desc = soup.get_text(" ", strip=True)[:3000]
        if len(desc) < 200 or "enable javascript" in desc.lower():
            return None
        return _job(company_name, title, _dept(title), desc, "", "html")
    except Exception:
        return None


# ── Shared helpers ────────────────────────────────────────────────────────────

def _job(company_name, title, dept, description, location, source) -> dict:
    return {
        "company_name": company_name,
        "role_title":   title[:255],
        "department":   dept or _dept(title),
        "description":  description,
        "location":     location,
        "keywords":     _keywords(title + " " + description),
        "posted_date":  "",
        "source":       source,
    }

def _keywords(text: str) -> dict:
    t = text.lower()
    return {
        "pivot":     [k for k in PIVOT_KEYWORDS     if k.lower() in t],
        "tech_debt": [k for k in TECH_DEBT_KEYWORDS if k.lower() in t],
        "fiscal":    [k for k in FISCAL_KEYWORDS    if k.lower() in t],
    }

def _dept(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["engineer","developer","sre","devops","architect",
                              "data","ml ","ai ","infrastructure","platform"]): return "Engineering"
    if any(x in t for x in ["sales","account","revenue","bdr","sdr","business dev"]): return "Sales"
    if any(x in t for x in ["market","growth","brand","demand","content"]): return "Marketing"
    if any(x in t for x in ["product","pm ","program manager"]): return "Product"
    if any(x in t for x in ["design","ux","ui ","creative"]): return "Design"
    if any(x in t for x in ["finance","accounting","fp&a"]): return "Finance"
    if any(x in t for x in ["hr","people","talent","recruit"]): return "HR"
    if any(x in t for x in ["legal","counsel","compliance"]): return "Legal"
    if any(x in t for x in ["security","infosec","cyber"]): return "Security"
    if any(x in t for x in ["customer success","csm","support"]): return "Customer Success"
    return "Other"

def _href_is_job(href: str) -> bool:
    return bool(re.search(
        r"/(job|position|opening|role|apply|opportunity)/|\?gh_jid=|/jobs/\d+|/postings/\w+",
        href, re.I
    ))

def _title_is_job(text: str) -> bool:
    if not 5 < len(text) < 120:
        return False
    if re.match(r"^(view all|browse|see all|open positions|all jobs|apply|more|back|filter)$",
                text.strip(), re.I):
        return False
    return bool(re.search(
        r"(engineer|manager|analyst|scientist|designer|director|lead|developer|"
        r"architect|specialist|coordinator|associate|head of|vp |representative|"
        r"recruiter|counsel|officer|executive)",
        text, re.I
    ))
