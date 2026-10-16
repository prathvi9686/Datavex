"""
GitHub Org Scraper (Free GitHub API)
Detects:
  - Commit frequency (activity level)
  - Open issue backlog (maintenance signal)
  - Language diversity
  - Legacy codebase signals from repo names/descriptions
  - Contributor trends
Rate limit: 60 req/hr unauthenticated, 5000/hr with token
"""
import os
import re
import statistics
from datetime import datetime, timezone
from loguru import logger

try:
    from github import Github, GithubException
except ImportError:
    Github = None


LEGACY_REPO_SIGNALS = [
    "legacy", "deprecated", "old-", "v1", "monolith", "migration",
    "archive", "technical-debt", "refactor", "rewrite"
]


def scrape_github_org(org_name: str, company_name: str, token: str | None = None) -> dict:
    """
    Fetch GitHub organization data and compute tech debt signals.
    org_name: GitHub org handle (e.g. 'microsoft', 'airbnb')
    token: optional GitHub PAT for higher rate limits (free to create)
    """
    if Github is None:
        logger.error("PyGithub not installed. Run: pip install PyGithub")
        return _empty_result(company_name, org_name)

    token = token or os.getenv("GITHUB_TOKEN")
    gh    = Github(token) if token else Github()

    try:
        org   = gh.get_organization(org_name)
        repos = list(org.get_repos(type="public", sort="updated"))[:30]  # top 30 active

        total_open_issues  = 0
        total_stars        = 0
        commit_freqs       = []
        languages          = {}
        legacy_signals     = []
        repo_summaries     = []

        for repo in repos:
            # Open issues
            total_open_issues += repo.open_issues_count
            total_stars       += repo.stargazers_count

            # Languages
            try:
                langs = repo.get_languages()
                for lang, bytes_count in langs.items():
                    languages[lang] = languages.get(lang, 0) + bytes_count
            except GithubException:
                pass

            # Commit frequency (last 52 weeks)
            try:
                weekly_commits = repo.get_stats_commit_activity()
                if weekly_commits:
                    recent_4_weeks = [w.total for w in list(weekly_commits)[-4:]]
                    avg = sum(recent_4_weeks) / 4 if recent_4_weeks else 0
                    commit_freqs.append(avg)
            except GithubException:
                pass

            # Legacy signals
            repo_text = (repo.name + " " + (repo.description or "")).lower()
            for signal in LEGACY_REPO_SIGNALS:
                if signal in repo_text:
                    legacy_signals.append({"repo": repo.name, "signal": signal})

            # How old is the repo's last commit?
            days_since_update = (datetime.now(timezone.utc) - repo.updated_at).days if repo.updated_at else 999

            repo_summaries.append({
                "name":               repo.name,
                "open_issues":        repo.open_issues_count,
                "stars":              repo.stargazers_count,
                "days_since_update":  days_since_update,
                "language":           repo.language,
            })

        # Sort languages by usage
        top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        top_languages = [lang for lang, _ in top_languages[:10]]

        avg_commit_freq = statistics.mean(commit_freqs) if commit_freqs else 0

        # Composite signals
        high_issue_repos = [r for r in repo_summaries if r["open_issues"] > 50]
        stale_repos      = [r for r in repo_summaries if r["days_since_update"] > 180]

        debt_assessment = _assess_github_debt(
            total_open_issues, len(repos), avg_commit_freq, legacy_signals, stale_repos
        )

        result = {
            "company_name":      company_name,
            "org_name":          org_name,
            "total_repos":       len(repos),
            "total_open_issues": total_open_issues,
            "avg_commit_freq":   round(avg_commit_freq, 2),
            "languages":         top_languages,
            "legacy_signals":    legacy_signals[:20],  # cap
            "github_debt": {
                "high_issue_repos": [r["name"] for r in high_issue_repos],
                "stale_repos":      [r["name"] for r in stale_repos],
                "debt_score":       debt_assessment["score"],
                "assessment":       debt_assessment["label"],
            },
            "top_repos": repo_summaries[:10],
        }

        logger.info(
            f"[{company_name}] GitHub: {len(repos)} repos, "
            f"{total_open_issues} open issues, "
            f"{len(legacy_signals)} legacy signals"
        )
        return result

    except Exception as e:
        logger.warning(f"GitHub scrape failed for org '{org_name}': {e}")
        return _empty_result(company_name, org_name)


def find_github_org(company_name: str) -> str | None:
    """
    Attempt to find a company's GitHub org by guessing common slug formats.
    e.g. "DataVex Inc" → tries "datavex", "datavex-inc", etc.
    """
    if Github is None:
        return None

    slugs = _generate_slugs(company_name)
    gh = Github(os.getenv("GITHUB_TOKEN"))

    for slug in slugs:
        try:
            org = gh.get_organization(slug)
            logger.info(f"Found GitHub org for '{company_name}': {org.login}")
            return org.login
        except GithubException:
            continue

    logger.debug(f"No GitHub org found for '{company_name}'")
    return None


def _generate_slugs(name: str) -> list[str]:
    """Generate possible GitHub org slug variants from a company name."""
    clean = re.sub(r"[^a-z0-9\s-]", "", name.lower()).strip()
    words = clean.split()
    return [
        "".join(words),            # datavex
        "-".join(words),           # data-vex
        words[0],                  # data
        clean.replace(" ", ""),
    ]


def _assess_github_debt(
    total_issues: int,
    repo_count: int,
    avg_commits: float,
    legacy_signals: list,
    stale_repos: list,
) -> dict:
    score = 0
    if repo_count > 0:
        issue_ratio = total_issues / repo_count
        if issue_ratio > 50:  score += 3
        elif issue_ratio > 20: score += 2
        elif issue_ratio > 5:  score += 1

    if avg_commits < 2:   score += 2
    elif avg_commits < 5: score += 1

    score += min(3, len(legacy_signals))
    score += min(2, len(stale_repos) // 3)

    score = min(10, score)
    label = (
        "Critical" if score >= 8 else
        "High"     if score >= 6 else
        "Medium"   if score >= 4 else
        "Low"      if score >= 2 else
        "Minimal"
    )
    return {"score": score, "label": label}


def _empty_result(company_name: str, org_name: str) -> dict:
    return {
        "company_name": company_name,
        "org_name":     org_name,
        "total_repos":  0,
        "total_open_issues": 0,
        "avg_commit_freq": 0.0,
        "languages": [],
        "legacy_signals": [],
        "github_debt": {"score": 0, "label": "Unknown"},
        "top_repos": [],
    }
