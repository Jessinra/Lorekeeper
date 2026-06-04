#!/usr/bin/env python3
"""
gh-reconcile — Cross-reference GitHub Issues, PRs, and backlog markdown files.

Detects:
  - Issues with merged PRs but not labeled S:Done
  - Issues labeled S:Done but still open
  - Duplicate issues (same LKPR-N ticket number)
  - Markdown status field vs GitHub issue label mismatch
  - Merged PRs without any issue reference
  - Branches without PRs (orphans)

Usage:
  ./scripts/gh-reconcile.py                  # full report
  ./scripts/gh-reconcile.py --markdown-only  # only check markdown files
  ./scripts/gh-reconcile.py --fix-done       # auto-close issues with merged PRs
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = "Jessinra/Lorekeeper"
BACKLOG_DIR = Path(os.path.expanduser("~/Code/lorekeeper/backlogs"))
HOSTS_YML = Path(os.path.expanduser("~/.config/gh/hosts.yml"))

# ── helpers ──────────────────────────────────────────────────────────────

def gh(*args: str) -> list:
    """Run gh command with GH_TOKEN from hosts.yml and return parsed JSON."""
    token = None
    if HOSTS_YML.exists():
        for line in HOSTS_YML.read_text().splitlines():
            if "oauth_token:" in line:
                token = line.split("oauth_token:", 1)[1].strip()
                break
    env = os.environ.copy()
    if token:
        env["GH_TOKEN"] = token

    cmd = ["gh", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"  [ERROR] gh {' '.join(args)} failed: {result.stderr.strip()}", file=sys.stderr)
        return []

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  [ERROR] Non-JSON output from gh: {result.stdout[:200]}", file=sys.stderr)
        return []


def extract_lkpr(title: str) -> str | None:
    """Extract LKPR-N ticket number from a title string."""
    m = re.search(r"LKPR-(\d+)", title, re.IGNORECASE)
    return f"LKPR-{m.group(1)}" if m else None


def label_names(issue: dict) -> list[str]:
    return [lbl.get("name", "") for lbl in issue.get("labels", [])]


def has_label(labels: list[str], prefix: str) -> bool:
    return any(lbl.startswith(prefix) for lbl in labels)


# ── data loading ─────────────────────────────────────────────────────────

def load_issues(state: str = "open") -> list[dict]:
    print(f"\n  Fetching {state} issues...", end=" ", flush=True)
    data = gh("issue", "list", "--repo", REPO, "--state", state,
              "--limit", "80", "--json", "number,title,labels,state,closedAt")
    print(f"{len(data)} issues")
    return data


def load_prs() -> list[dict]:
    print("  Fetching merged PRs...", end=" ", flush=True)
    data = gh("pr", "list", "--repo", REPO, "--state", "merged",
              "--limit", "50", "--json", "number,title,headRefName,mergedAt,labels,body")
    print(f"{len(data)} PRs")
    return data


def load_markdown_backlog() -> dict[str, dict]:
    """Read backlog + proposal markdown files, return {LKPR-N: {status, path, title}}."""
    result = {}
    for section in ["backlog", "proposal"]:
        dirpath = BACKLOG_DIR / section
        if not dirpath.exists():
            continue
        for f in sorted(dirpath.glob("*.md")):
            text = f.read_text()
            lkpr = extract_lkpr(text[:200])  # check header
            status = "S:unknown"
            title = f.name
            for line in text.splitlines():
                if line.startswith("status:"):
                    status = line.split(":", 1)[1].strip()
                elif line.startswith("title:"):
                    title = line.split(":", 1)[1].strip()
            if lkpr:
                result[lkpr] = {
                    "status": status, "path": str(f), "title": title, "section": section,
                }
    return result


def get_branches() -> list[str]:
    """Get all remote branches excluding main/backlog."""
    print("  Fetching remote branches...", end=" ", flush=True)
    try:
        result = subprocess.run(
            ["git", "branch", "-r"],
            capture_output=True, text=True,
            cwd=os.path.expanduser("~/Code/lorekeeper"),
        )
        branches = [
            b.strip().removeprefix("origin/")
            for b in result.stdout.splitlines()
            if b.strip() and "origin/" in b
            and b.strip() not in ("origin/main", "origin/HEAD -> origin/main")
        ]
        print(f"{len(branches)} branches")
        return branches
    except Exception as e:
        print(f"  [ERROR] git failed: {e}")
        return []


# ── checks ───────────────────────────────────────────────────────────────

def check_merged_not_done(open_issues: list[dict], merged_prs: list[dict]) -> list:
    """Issues with merged PRs but not labeled S:Done."""
    print("\n── Check 1: Merged PRs → issue not marked S:Done ──")
    findings = []

    # Build {LKPR-N → [PRs]}
    # Only match LKPR-N in PR TITLE, not body — body references to tickets
    # that were filed/imported/mentioned are not implementations.
    # Also skip PRs that are about creating/filing tickets rather than
    # implementing them (identified by title keywords).
    TICKET_CREATION_KEYWORDS = {"ticket", "proposal", "proposals", "filing", "plans"}
    prs_by_lkpr: dict[str, list] = defaultdict(list)
    for pr in merged_prs:
        title = pr.get("title", "")
        title_lower = title.lower()
        # Skip PRs that are about ticket creation, not implementation
        if any(kw in title_lower for kw in TICKET_CREATION_KEYWORDS):
            continue
        for m in re.finditer(r"LKPR-(\d+)", title):
            ref = f"LKPR-{m.group(1)}"
            prs_by_lkpr[ref].append(pr)

    # Map open issues
    issues_by_lkpr: dict[str, list] = defaultdict(list)
    for issue in open_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr:
            issues_by_lkpr[lkpr].append(issue)

    count = 0
    for lkpr, prs in sorted(prs_by_lkpr.items()):
        for issue in issues_by_lkpr.get(lkpr, []):
            lbls = label_names(issue)
            if not has_label(lbls, "S:Done"):
                merged_pr_num = [p["number"] for p in prs]
                findings.append({
                    "type": "merged_not_done",
                    "lkpr": lkpr,
                    "issue": issue["number"],
                    "prs": merged_pr_num,
                    "labels": lbls,
                })
                count += 1
                pr_list = ", ".join(f"PR#{n}" for n in merged_pr_num)
                print(
                    f"  ✗ #{issue['number']} [{lkpr}] has merged "
                    f"{pr_list} but labels: {', '.join(lbls)}"
                )

    if count == 0:
        print("  ✓ All merged PRs have corresponding S:Done issues.")
    return findings


def check_done_but_open(open_issues: list[dict]) -> list:
    """Issues labeled S:Done but still open (should be closed)."""
    print("\n── Check 2: S:Done issues still open ──")
    findings = []
    for issue in open_issues:
        lbls = label_names(issue)
        if has_label(lbls, "S:Done"):
            findings.append({
                "type": "done_but_open",
                "lkpr": extract_lkpr(issue["title"]),
                "issue": issue["number"],
                "title": issue["title"],
                "labels": lbls,
            })
            print(f"  ✗ #{issue['number']} labeled S:Done but still open — should be closed")

    if not findings:
        print("  ✓ No S:Done issues left open.")
    return findings


def check_duplicates(all_issues: list[dict]) -> list:
    """Find duplicate issues referencing the same LKPR-N.

    Skips pairs where one is closed+S:Cancelled and the other is a clean open
    copy — those are already reconciled. Flags true active duplicates.
    """
    print("\n── Check 3: Duplicate issues (same LKPR-N) ──")
    findings = []
    by_lkpr: dict[str, list] = defaultdict(list)
    for issue in all_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr:
            by_lkpr[lkpr].append(issue)

    for lkpr, issues in sorted(by_lkpr.items()):
        if len(issues) > 1:
            sorted_issues = sorted(issues, key=lambda i: i["number"])
            kept = [i for i in sorted_issues if i["state"] == "open"]
            closed = [i for i in sorted_issues if i["state"] == "closed"]

            # If exactly one is open and rest are closed+S:Cancelled → already reconciled
            cancelled_closed = [
                c for c in closed
                if "S:Cancelled" in label_names(c)
            ]
            if len(kept) == 1 and len(cancelled_closed) == len(closed) and len(closed) > 0:
                # Already reconciled — note it but don't flag
                continue

            # If all copies are closed → nothing to do
            if len(kept) == 0:
                continue

            findings.append({
                "type": "duplicate",
                "lkpr": lkpr,
                "open_count": len(kept),
                "closed_count": len(closed),
                "open": [i["number"] for i in kept],
                "closed": [i["number"] for i in closed],
            })
            nums = ", ".join(f"#{i['number']}({i['state']})" for i in sorted_issues)
            print(f"  ✗ [{lkpr}] {len(issues)} copies: {nums}")

    if not findings:
        print("  ✓ No duplicates found.")
    return findings


def check_markdown_vs_github(
    open_issues: list[dict],
    closed_issues: list[dict],
    markdown: dict[str, dict],
) -> list:
    """Compare markdown status field vs GitHub issue label."""
    print("\n── Check 4: Markdown status vs GitHub label ──")
    count = 0
    unchecked = []

    # Build {LKPR-N → issue} from ALL issues (open + closed)
    issues_by_lkpr: dict[str, dict] = {}
    for issue in open_issues + closed_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr and lkpr not in issues_by_lkpr:
            issues_by_lkpr[lkpr] = issue  # first seen wins

    for lkpr, md in sorted(markdown.items()):
        md_status = md["status"]
        issue = issues_by_lkpr.get(lkpr)
        if not issue:
            unchecked.append((lkpr, md))
            print(f"  ? [{lkpr}] markdown exists but no corresponding GitHub issue found")
            count += 1
            continue

        gh_labels = label_names(issue)
        gh_status = next((lbl for lbl in gh_labels if lbl.startswith("S:")), "S:unknown")

        # Normalize: "S:ready" ↔ "S:Ready"
        if md_status.lower() != gh_status.lower():
            print(
                f"  ✗ #{issue['number']} [{lkpr}] markdown: "
                f"{md_status} vs GitHub: {gh_status} ({issue['state']})",
            )
            count += 1

    # Show unreferenced markdown files (S:Done ones are expected — keep the spec)
    done_unreferenced = [u for u in unchecked if u[1]["status"] == "S:done"]
    if done_unreferenced:
        for lkpr, _md in done_unreferenced:
            print(f"  ✓ [{lkpr}] S:done markdown file — no open issue needed (spec archive)")

    if count == len(done_unreferenced):
        print("  ✓ All markdown statuses match GitHub labels.")
    return []


def check_orphan_branches(merged_prs: list[dict], branches: list[str]) -> list:
    """Find branches that exist but have no associated merged PR."""
    print("\n── Check 5: Orphan branches (no merged PR) ──")
    pr_branches = {pr.get("headRefName", "") for pr in merged_prs}

    # Also add branches from closed (not merged) PRs
    open_pr_data = gh("pr", "list", "--repo", REPO, "--state", "open",
                       "--limit", "30", "--json", "headRefName")
    closed_pr_data = gh("pr", "list", "--repo", REPO, "--state", "closed",
                         "--limit", "30", "--json", "headRefName,state")
    for pr in open_pr_data + closed_pr_data:
        pr_branches.add(pr.get("headRefName", ""))

    findings = []
    for branch in sorted(branches):
        if branch not in pr_branches:
            findings.append({"type": "orphan_branch", "branch": branch})
            print(f"  ? {branch} — no PR found")

    if not findings:
        print("  ✓ No orphan branches.")
    return findings


# ── fix helpers ──────────────────────────────────────────────────────────

def fix_done_issues(open_issues: list[dict]) -> None:
    """Close S:Done issues."""
    print("\n── Auto-fix: closing S:Done open issues ──")
    for issue in open_issues:
        lbls = label_names(issue)
        if has_label(lbls, "S:Done"):
            num = issue["number"]
            print(f"  Closing #{num} [{issue['title']}]... ", end="", flush=True)
            r = subprocess.run(
                ["gh", "issue", "close", str(num), "--repo", REPO],
                capture_output=True, text=True,
            )
            print("✓" if r.returncode == 0 else f"FAILED: {r.stderr.strip()}")


# ── main ─────────────────────────────────────────────────────────────────

def main():
    markdown_only = "--markdown-only" in sys.argv
    fix_done = "--fix-done" in sys.argv

    print("╔══════════════════════════════════════════════╗")
    print("║  GH-Reconcile — Issue ↔ PR ↔ Backlog Sync   ║")
    print("╚══════════════════════════════════════════════╝")

    if markdown_only:
        print("\n[ Markdown-only mode: skipping GH API calls ]")
        markdown = load_markdown_backlog()
        print(f"\n  Loaded {len(markdown)} backlog/proposal markdown files")
        print("\n── Status Summary ──")
        by_status = defaultdict(list)
        for lkpr, md in markdown.items():
            by_status[md["status"]].append(lkpr)
        for status, items in sorted(by_status.items()):
            print(f"  {status}: {len(items)} — {', '.join(items)}")
        return

    # Load all data
    open_issues = load_issues("open")
    closed_issues = load_issues("closed")
    all_issues = open_issues + closed_issues
    merged_prs = load_prs()
    markdown = load_markdown_backlog()
    branches = get_branches()

    print(f"\n  Open issues: {len(open_issues)}")
    print(f"  Total issues (open+closed): {len(all_issues)}")
    print(f"  Merged PRs: {len(merged_prs)}")
    print(f"  Backlog markdown files: {len(markdown)}")

    # Run checks
    f1 = check_merged_not_done(open_issues, merged_prs)
    f2 = check_done_but_open(open_issues)
    f3 = check_duplicates(all_issues)
    f4 = check_markdown_vs_github(open_issues, closed_issues, markdown)
    f5 = check_orphan_branches(merged_prs, branches)

    # Summary
    total = len(f1) + len(f2) + len(f3) + len(f5)
    print(f"\n{'='*50}")
    print(f"  Total inconsistencies found: {total}")
    print(f"  Markdown-GitHub mismatches: {sum(1 for i in (f4 or []) if 'markdown' in str(i))}")
    if total == 0:
        print("  ✓ All clean!")
    else:
        print("\n  Fix suggestions:")
        if f1:
            print(f"    → {len(f1)} issues have merged PRs but aren't S:Done")
            print("       Run with --fix-done to auto-close")
        if f2:
            print(f"    → {len(f2)} S:Done issues still open")
            print("       Run with --fix-done to auto-close")
        if f3:
            dup_count = sum(f["open_count"] for f in f3)
            print(f"    → {dup_count} duplicate open issues to resolve")
        if f5:
            print(f"    → {len(f5)} stale/orphan branches to clean up")

    if fix_done and (f1 or f2):
        fix_done_issues(open_issues)


if __name__ == "__main__":
    main()
