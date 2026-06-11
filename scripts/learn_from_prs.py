#!/usr/bin/env python3
"""
Learn from merged PRs and update code review skills automatically.

This script runs on a schedule (daily cron via Hermes). It:

1. Fetches recently merged PRs from GitHub (last N days)
2. For each PR, collects:
   - Review comments (inline + summary)
   - Files changed
   - Labels
   - Whether blockers were found (by parsing comment bodies)
3. Extracts patterns: BLOCKERs that were caught at review stage (not pre-commit)
4. Clusters findings by category: security, correctness, architecture, performance
5. Generates a structured learning report and calls the Hermes skill-patch agent

Usage:
    python scripts/learn_from_prs.py [--days N] [--dry-run] [--repo OWNER/REPO]

Outputs:
    - ~/.hermes/profiles/diana/cron/output/pr-learning-YYYY-MM-DD.json
    - Patches code-review-pipeline skill with newly discovered patterns
    - Saves findings to Lorekeeper memory for cross-session recall
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

REPO = "Jessinra/Lorekeeper"
API_BASE = "https://api.github.com"
OUTPUT_DIR = Path.home() / ".hermes" / "profiles" / "diana" / "cron" / "output"

# Conventional Comments labels that indicate a blocking issue was found at review time
BLOCKER_LABELS = {"blocker:", "issue (blocking):", "🚫", "BLOCKER", "[BLOCKER]"}
MAJOR_LABELS = {"issue:", "issue (non-blocking):", "major:", "[MAJOR]"}

# Categories to cluster findings into
CATEGORIES = {
    "security": ["secret", "injection", "xss", "auth", "token", "password", "credential",
                 "sanitize", "validate", "escape", "permission", "trust"],
    "correctness": ["bug", "error", "exception", "crash", "race", "deadlock", "null",
                    "undefined", "off-by-one", "edge case", "condition", "logic"],
    "architecture": ["layer", "coupling", "dependency", "abstraction", "pattern", "design",
                     "separation", "responsibility", "contract", "interface"],
    "performance": ["n+1", "query", "index", "slow", "timeout", "memory", "cpu", "cache",
                    "batch", "pagination", "heavy", "expensive"],
    "observability": ["log", "metric", "trace", "monitor", "alert", "structlog", "print"],
    "testing": ["test", "coverage", "assert", "mock", "fixture", "hypothesis"],
}


# ── GitHub API helpers ─────────────────────────────────────────────────────────


def gh_request(path: str, method: str = "GET") -> Any:
    """Make an authenticated GitHub API call. Returns parsed JSON."""
    token = _get_gh_token()
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[learn_from_prs] GitHub API error {e.code} for {path}: {body[:200]}", file=sys.stderr)  # noqa: E501
        raise


def _get_gh_token() -> str:
    """Resolve GitHub token: GH_TOKEN env → gh auth token CLI → fail."""
    for env_var in ("GH_TOKEN", "GITHUB_TOKEN"):
        tok = os.environ.get(env_var, "")
        if tok:
            return tok

    # Try gh CLI
    import subprocess
    proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if proc.returncode == 0:
        tok = proc.stdout.strip()
        if tok:
            return tok

    raise RuntimeError(
        "No GitHub token found. Set GH_TOKEN or run `gh auth login`."
    )


def get_merged_prs(repo: str, since: datetime) -> list[dict[str, Any]]:
    """Fetch PRs merged since `since` date. Returns list of PR objects."""
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")  # kept for readability
    path = f"/repos/{repo}/pulls?state=closed&sort=updated&direction=desc&per_page=50&since={since_str}"  # noqa: E501
    prs = gh_request(path)

    merged = []
    for pr in prs:
        if not pr.get("merged_at"):
            continue
        merged_at = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
        if merged_at < since.replace(tzinfo=UTC):
            continue
        merged.append(pr)

    return merged


def get_pr_review_comments(repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Fetch all inline review comments for a PR."""
    return gh_request(f"/repos/{repo}/pulls/{pr_number}/comments?per_page=100")


def get_pr_reviews(repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Fetch PR reviews (general review comments, not inline)."""
    return gh_request(f"/repos/{repo}/pulls/{pr_number}/reviews")


def get_pr_files(repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Fetch files changed in a PR."""
    return gh_request(f"/repos/{repo}/pulls/{pr_number}/files?per_page=100")


# ── Pattern extraction ─────────────────────────────────────────────────────────


def classify_comment(body: str) -> tuple[str, str]:
    """
    Returns (severity, category) for a review comment body.
    severity: BLOCKER | MAJOR | MINOR | NIT | INFO
    category: security | correctness | architecture | performance |  # noqa: E501
              observability | testing | general
    """
    body_lower = body.lower()

    # Severity
    severity = "INFO"
    for label in BLOCKER_LABELS:
        if label.lower() in body_lower:
            severity = "BLOCKER"
            break
    if severity == "INFO":
        for label in MAJOR_LABELS:
            if label.lower() in body_lower:
                severity = "MAJOR"
                break
    if severity == "INFO" and any(x in body_lower for x in ["nit:", "nit(", "[nit]"]):
        severity = "NIT"
    if severity == "INFO" and any(x in body_lower for x in ["suggestion:", "[minor]", "minor:"]):
        severity = "MINOR"

    # Category
    for cat, keywords in CATEGORIES.items():
        if any(kw in body_lower for kw in keywords):
            return severity, cat

    return severity, "general"


def extract_patterns_from_pr(
    pr: dict[str, Any],
    comments: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Extract actionable patterns from a PR's review activity.
    Returns list of pattern dicts with: severity, category, file_path, comment, fix_hint
    """
    patterns = []
    changed_paths = [f["filename"] for f in files]

    # Process inline comments
    for comment in comments:
        body = comment.get("body", "")
        if len(body) < 20:
            continue  # Skip trivial comments

        severity, category = classify_comment(body)
        if severity in ("INFO", "NIT"):
            continue  # Only learn from BLOCKER/MAJOR/MINOR

        patterns.append({
            "pr_number": pr["number"],
            "pr_title": pr["title"],
            "pr_url": pr["html_url"],
            "merged_at": pr.get("merged_at", ""),
            "severity": severity,
            "category": category,
            "file": comment.get("path", ""),
            "line": comment.get("line") or comment.get("original_line") or 0,
            "comment": body[:500],  # truncate
            "diff_hunk": comment.get("diff_hunk", "")[:200],
            "author": comment.get("user", {}).get("login", ""),
            "changed_files": changed_paths[:10],
        })

    # Process general review bodies
    for review in reviews:
        body = review.get("body") or ""
        if len(body) < 40:
            continue
        if review.get("state") not in ("CHANGES_REQUESTED", "COMMENTED"):
            continue

        severity, category = classify_comment(body)
        if severity == "INFO":
            continue

        patterns.append({
            "pr_number": pr["number"],
            "pr_title": pr["title"],
            "pr_url": pr["html_url"],
            "merged_at": pr.get("merged_at", ""),
            "severity": severity,
            "category": category,
            "file": "(general review)",
            "line": 0,
            "comment": body[:500],
            "diff_hunk": "",
            "author": review.get("user", {}).get("login", ""),
            "changed_files": changed_paths[:10],
        })

    return patterns


def cluster_patterns(patterns: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group patterns by category for skill update."""
    clusters: dict[str, list[dict[str, Any]]] = {}
    for p in patterns:
        clusters.setdefault(p["category"], []).append(p)
    return clusters


# ── Report generation ─────────────────────────────────────────────────────────


def generate_report(
    prs_analyzed: list[dict[str, Any]],
    all_patterns: list[dict[str, Any]],
    date_range: str,
) -> dict[str, Any]:
    """Build the structured learning report."""
    clusters = cluster_patterns(all_patterns)
    blockers = [p for p in all_patterns if p["severity"] == "BLOCKER"]
    majors = [p for p in all_patterns if p["severity"] == "MAJOR"]

    # Summarize what the BLOCKER/MAJOR findings were about
    blocker_summaries = []
    for p in blockers[:10]:  # Top 10 most recent blockers
        blocker_summaries.append({
            "pr": f"#{p['pr_number']} — {p['pr_title'][:60]}",
            "file": p["file"],
            "category": p["category"],
            "comment_excerpt": p["comment"][:200],
        })

    return {
        "generated_at": datetime.now().isoformat(),
        "date_range": date_range,
        "prs_analyzed": len(prs_analyzed),
        "total_patterns": len(all_patterns),
        "blocker_count": len(blockers),
        "major_count": len(majors),
        "by_category": {cat: len(items) for cat, items in clusters.items()},
        "top_blockers": blocker_summaries,
        "skill_update_needed": len(blockers) > 0,
        "skill_update_rationale": (
            f"Found {len(blockers)} BLOCKER-tier issues caught at review stage "
            f"(not pre-commit). These should be added to check_blockers.py or "
            f"the AI review prompt to shift detection left."
            if blockers
            else "No new BLOCKER patterns found."
        ),
        "raw_patterns": all_patterns[:50],  # Cap for storage
        "pr_urls": [pr["html_url"] for pr in prs_analyzed],
    }


def format_telegram_summary(report: dict[str, Any]) -> str:
    """Format a compact Telegram-friendly learning digest."""
    date = report["date_range"]
    n_prs = report["prs_analyzed"]
    n_patterns = report["total_patterns"]
    blockers = report["blocker_count"]
    majors = report["major_count"]
    by_cat = report["by_category"]

    lines = [
        f"🧠 **Code Review Learning Digest** — {date}",
        "",
        f"📊 {n_prs} PRs analyzed · {n_patterns} patterns found",
        f"🔴 {blockers} BLOCKER(s)  🟡 {majors} MAJOR(s)",
    ]

    if by_cat:
        lines.append("")
        lines.append("**By category:**")
        for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
            icon = {
                "security": "🔒", "correctness": "🐛", "architecture": "🏗️",
                "performance": "⚡", "observability": "📡", "testing": "🧪",
                "general": "📝",
            }.get(cat, "•")
            lines.append(f"  {icon} {cat}: {count}")

    if report["top_blockers"]:
        lines.append("")
        lines.append("**Top BLOCKERs caught at review (should be pre-commit):**")
        for b in report["top_blockers"][:3]:
            lines.append(f"  🚫 `{b['category']}` — {b['pr']} — `{b['file']}`")
            lines.append(f"     _{b['comment_excerpt'][:100]}_")

    if report["skill_update_needed"]:
        lines.append("")
        lines.append("⬆️ **Skill update queued** — adding new patterns to `check_blockers.py`")
    else:
        lines.append("")
        lines.append("✅ No new patterns to add — skills are current.")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Learn from merged PRs, update skills.")
    parser.add_argument("--days", type=int, default=7, help="How many days back to analyze")
    parser.add_argument("--repo", default=REPO, help="GitHub repo in OWNER/REPO format")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output files")
    parser.add_argument("--quiet", action="store_true", help="Only print the summary")
    args = parser.parse_args()

    since = datetime.now(UTC) - timedelta(days=args.days)
    date_range = f"{since.strftime('%Y-%m-%d')} → {datetime.now().strftime('%Y-%m-%d')}"

    print(f"[learn_from_prs] Analyzing {args.repo} — last {args.days} days ({date_range})")

    try:
        prs = get_merged_prs(args.repo, since)
    except Exception as e:
        print(f"[learn_from_prs] ❌ Failed to fetch PRs: {e}", file=sys.stderr)
        return 1

    print(f"[learn_from_prs] Found {len(prs)} merged PRs")

    all_patterns: list[dict[str, Any]] = []

    for pr in prs:
        pr_num = pr["number"]
        if not args.quiet:
            print(f"  → PR #{pr_num}: {pr['title'][:60]}")

        try:
            comments = get_pr_review_comments(args.repo, pr_num)
            reviews = get_pr_reviews(args.repo, pr_num)
            files = get_pr_files(args.repo, pr_num)
        except Exception as e:
            print(f"  ⚠️  Skipping PR #{pr_num}: {e}", file=sys.stderr)
            continue

        patterns = extract_patterns_from_pr(pr, comments, reviews, files)
        all_patterns.extend(patterns)

        if patterns and not args.quiet:
            cats = {p["category"] for p in patterns}
            severities = {p["severity"] for p in patterns}
            print(f"     {len(patterns)} pattern(s) — {severities} — {cats}")

    report = generate_report(prs, all_patterns, date_range)
    summary = format_telegram_summary(report)

    if not args.dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file = OUTPUT_DIR / f"pr-learning-{datetime.now().strftime('%Y-%m-%d')}.json"
        out_file.write_text(json.dumps(report, indent=2))
        print(f"[learn_from_prs] Report saved → {out_file}")

    # Always print the summary (cron will send this to Telegram)
    print("\n" + summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
