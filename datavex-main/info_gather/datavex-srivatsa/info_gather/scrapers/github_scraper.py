"""
GitHub Org Scraper — fast, fails immediately on rate limits.
Set GITHUB_TOKEN in .env for 5000 req/hr.
Skips commit activity stats (slow API) — uses repo metadata only.
"""
import os
import re
from datetime import datetime, timezone
from loguru import logger

try:
    from github import Github, GithubException, RateLimitExceededException
except ImportError:
    Github = None

LEGACY_REPO_SIGNALS = [
    "legacy", "deprecated", "old-", "v1", "monolith", "migration",
    "archive", "technical-debt", "refactor", "rewrite"
]
MAX_REPOS = 20


def scrape_github_org(org_name: str, company_name: str, token: str | None = None) -> dict:
    if Github is None:
        logger.error("PyGithub not installed.")
        return _empty(company_name, org_name)

    token = token or os.getenv("GITHUB_TOKEN")
    if not token:
        logger.warning(f"[{company_name}] No GITHUB_TOKEN in .env — GitHub skipped")
        return _empty(company_name, org_name)

    # retry=None prevents urllib3 from sleeping on 403s
    gh = Github(token, timeout=10, retry=None)

    try:
        rate = gh.get_rate_limit()
        if rate.core.remaining < 30:
            logger.warning(f"[{company_name}] GitHub rate limit low ({rate.core.remaining} left) — skipping")
            return _empty(company_name, org_name)

        org   = gh.get_organization(org_name)
        repos = list(org.get_repos(type="public", sort="updated"))[:MAX_REPOS]

        total_open_issues = 0
        languages         = {}
        legacy_signals    = []
        repo_summaries    = []
        stale_count       = 0

        for repo in repos:
            total_open_issues += repo.open_issues_count

            # Languages — quick metadata call
            try:
                for lang, b in repo.get_languages().items():
                    languages[lang] = languages.get(lang, 0) + b
            except Exception:
                pass

            # Legacy signals from repo name + description (no API call)
            repo_text = (repo.name + " " + (repo.description or "")).lower()
            for signal in LEGACY_REPO_SIGNALS:
                if signal in repo_text:
                    legacy_signals.append({"repo": repo.name, "signal": signal})

            days_since = (datetime.now(timezone.utc) - repo.updated_at).days if repo.updated_at else 999
            if days_since > 180:
                stale_count += 1

            repo_summaries.append({
                "name":              repo.name,
                "open_issues":       repo.open_issues_count,
                "stars":             repo.stargazers_count,
                "days_since_update": days_since,
                "language":          repo.language,
            })

        top_langs = [l for l, _ in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]]
        debt      = _assess_debt(total_open_issues, len(repos), legacy_signals, stale_count)

        logger.success(f"[{company_name}] GitHub: {len(repos)} repos | {total_open_issues} issues | debt={debt['label']}")

        return {
            "company_name":      company_name,
            "org_name":          org_name,
            "total_repos":       len(repos),
            "total_open_issues": total_open_issues,
            "avg_commit_freq":   0.0,   # skipped — too slow
            "languages":         top_langs,
            "legacy_signals":    legacy_signals[:20],
            "github_debt":       debt,
            "top_repos":         repo_summaries[:10],
        }

    except RateLimitExceededException:
        logger.warning(f"[{company_name}] GitHub rate limit hit — skipping")
        return _empty(company_name, org_name)
    except GithubException as e:
        if e.status == 404:
            logger.warning(f"[{company_name}] GitHub org '{org_name}' not found")
        else:
            logger.warning(f"[{company_name}] GitHub error {e.status}: {e.data}")
        return _empty(company_name, org_name)
    except Exception as e:
        logger.warning(f"[{company_name}] GitHub failed: {e}")
        return _empty(company_name, org_name)


def find_github_org(company_name: str) -> str | None:
    if Github is None or not os.getenv("GITHUB_TOKEN"):
        return None
    gh = Github(os.getenv("GITHUB_TOKEN"), timeout=10, retry=None)
    for slug in _slugs(company_name):
        try:
            return gh.get_organization(slug).login
        except Exception:
            continue
    return None


def _slugs(name: str) -> list[str]:
    clean = re.sub(r"[^a-z0-9\s]", "", name.lower()).strip()
    words = clean.split()
    seen, out = set(), []
    for s in ["".join(words), "-".join(words), words[0] if words else ""]:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _assess_debt(total_issues, repo_count, legacy_signals, stale_count) -> dict:
    score = 0
    if repo_count > 0:
        r = total_issues / repo_count
        score += 3 if r > 50 else 2 if r > 20 else 1 if r > 5 else 0
    score += min(3, len(legacy_signals))
    score += min(2, stale_count // 3)
    score  = min(10, score)
    label  = ("Critical" if score >= 8 else "High" if score >= 6 else
              "Medium"   if score >= 4 else "Low"  if score >= 2 else "Minimal")
    return {"score": score, "label": label}


def _empty(company_name, org_name) -> dict:
    return {
        "company_name": company_name, "org_name": org_name,
        "total_repos": 0, "total_open_issues": 0, "avg_commit_freq": 0.0,
        "languages": [], "legacy_signals": [],
        "github_debt": {"score": 0, "label": "Unknown"}, "top_repos": [],
    }
