"""
Tech Stack Detector (Free - no BuiltWith API needed)
Detects frameworks, languages, and legacy signals from:
  1. HTTP response headers
  2. HTML source fingerprinting
  3. Script/link tag analysis
"""
import re
from bs4 import BeautifulSoup
from loguru import logger
from utils.http import safe_get, get_session


# Fingerprint rules: (pattern_in_html_or_header, tech_name, is_legacy)
FINGERPRINTS = [
    # JavaScript frameworks
    (r'__NEXT_DATA__|/_next/static',          "Next.js",        False),
    (r'ng-version|angular\.min\.js',          "AngularJS",      True),   # AngularJS = legacy
    (r'ng-app|angular\.js',                   "AngularJS",      True),
    (r'react\.development|react-dom',         "React",          False),
    (r'vue\.min\.js|vuejs',                   "Vue.js",         False),
    (r'ember\.min|emberjs',                   "Ember.js",       True),
    (r'backbone\.js|underscore\.js',          "Backbone.js",    True),
    (r'jquery\.min\.js|jquery-\d',            "jQuery",         True),   # jQuery alone = legacy

    # CMS / Platforms
    (r'/wp-content/|wp-json',                 "WordPress",      True),
    (r'drupal\.js|drupal-behaviors',          "Drupal",         True),
    (r'joomla',                               "Joomla",         True),
    (r'squarespace\.com',                     "Squarespace",    False),
    (r'cdn\.shopify\.com',                    "Shopify",        False),

    # Analytics / Tracking
    (r'google-analytics\.com|gtag\(',         "Google Analytics", False),
    (r'segment\.com/analytics',               "Segment",        False),
    (r'mixpanel',                             "Mixpanel",       False),
    (r'amplitude\.com',                       "Amplitude",      False),
    (r'heap\.io|heapanalytics',               "Heap",           False),
    (r'fullstory\.com',                       "FullStory",      False),

    # Backend / Infra (from headers)
    (r'x-powered-by.*php',                    "PHP",            True),
    (r'x-powered-by.*asp\.net',               "ASP.NET",        True),
    (r'server.*apache',                       "Apache",         True),
    (r'server.*nginx',                        "Nginx",          False),
    (r'x-powered-by.*express',                "Express.js",     False),

    # Cloud / Modern infra
    (r'cloudfront\.net|x-amz',               "AWS CloudFront", False),
    (r'vercel\.com|x-vercel',                 "Vercel",         False),
    (r'netlify',                              "Netlify",        False),
    (r'fastly\.com',                          "Fastly CDN",     False),

    # Data / AI signals
    (r'tensorflow|pytorch|ml-platform',      "ML Framework",   False),
    (r'databricks|snowflake|dbt',             "Modern Data Stack", False),
]

# Multiple legacy frameworks at once = high debt
LEGACY_THRESHOLD = 3


def detect_tech_stack(domain: str, company_name: str) -> dict:
    """
    Fetch company homepage and detect tech stack.
    Returns structured dict ready for DB insertion.
    """
    url = _normalize_url(domain)
    session = get_session()
    frameworks, languages, raw_headers, debt_signals = [], [], {}, []

    try:
        resp = safe_get(url, session, timeout=15)
        html  = resp.text
        headers_lower = {k.lower(): v.lower() for k, v in resp.headers.items()}

        # Combine HTML + headers for scanning
        combined = html + " " + str(headers_lower)

        detected = _run_fingerprints(combined)
        frameworks = [d["tech"] for d in detected]
        debt_signals = [d["tech"] for d in detected if d["is_legacy"]]

        # Extract inline languages from script src
        languages = _detect_languages(html, headers_lower)

        # Save relevant headers
        raw_headers = {
            k: headers_lower[k]
            for k in ["server", "x-powered-by", "x-frame-options", "content-type", "via"]
            if k in headers_lower
        }

        logger.info(
            f"[{company_name}] Stack: {frameworks} | Legacy signals: {debt_signals}"
        )

    except Exception as e:
        logger.warning(f"Tech stack detect failed ({domain}): {e}")

    legacy_score = min(10, len(debt_signals) * 2.5)  # crude 0-10 score

    return {
        "company_name": company_name,
        "domain":       domain,
        "frameworks":   frameworks,
        "languages":    languages,
        "raw_headers":  raw_headers,
        "debt_signals": {
            "detected_legacy_tech": debt_signals,
            "legacy_score":         legacy_score,
            "assessment":           _assess_debt(debt_signals),
        },
    }


def _run_fingerprints(text: str) -> list[dict]:
    found = []
    seen  = set()
    for pattern, tech, is_legacy in FINGERPRINTS:
        if re.search(pattern, text, re.I) and tech not in seen:
            seen.add(tech)
            found.append({"tech": tech, "is_legacy": is_legacy})
    return found


def _detect_languages(html: str, headers: dict) -> list[str]:
    langs = []
    if re.search(r'\.py|python', html, re.I):         langs.append("Python")
    if re.search(r'\.rb|ruby|rails', html, re.I):     langs.append("Ruby")
    if re.search(r'\.java|spring', html, re.I):       langs.append("Java")
    if re.search(r'\.php', html, re.I):               langs.append("PHP")
    if re.search(r'\.ts|typescript', html, re.I):     langs.append("TypeScript")
    if "php" in headers.get("x-powered-by", ""):      langs.append("PHP")
    if "asp.net" in headers.get("x-powered-by", ""):  langs.append("C#/.NET")
    return list(set(langs))


def _assess_debt(debt_signals: list[str]) -> str:
    n = len(debt_signals)
    if n == 0:  return "Low — modern stack detected"
    if n == 1:  return "Low-Medium — one legacy component"
    if n == 2:  return "Medium — multiple legacy dependencies"
    if n == 3:  return "Medium-High — several legacy systems"
    return      "High — significant legacy stack detected"


def _normalize_url(domain: str) -> str:
    if domain.startswith("http"):
        return domain
    return f"https://{domain}"
