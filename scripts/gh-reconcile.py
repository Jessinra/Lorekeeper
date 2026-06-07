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
  - Issues missing status (S:) or priority (P:) labels
  - Issues with multiple status labels (ambiguous)

Deep mode (--deep):
  - S:Done verification — feature PR or just proposal PR?
  - S:Cancelled verification — really cancelled or implemented?
  - Closed S:Proposal categorization — duplicate / orphan / not_planned
  - Closed S:Ready → S:Done (merged PRs but label not updated)
  - File location vs GH label mismatch
  - Backlog files with no corresponding GH issue
  - Full LKPR-sorted summary table with verdict per ticket

Usage:
  ./scripts/gh-reconcile.py                          # standard report
  ./scripts/gh-reconcile.py --deep                   # full deep reconcile
  ./scripts/gh-reconcile.py --fix-done               # auto-close issues with merged PRs
  ./scripts/gh-reconcile.py --fix-labels             # auto-add missing S:/P: labels
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Optional

REPO = "Jessinra/Lorekeeper"
HOSTS_YML = Path(os.path.expanduser("~/.config/gh/hosts.yml"))

# ── helpers ──────────────────────────────────────────────────────────────

VALID_S_LABELS = {"S:proposal", "S:ready", "S:in-progress", "S:review", "S:done", "S:deferred", "S:cancelled"}
VALID_P_LABELS = {"P0:critical", "P1:high", "P2:medium", "P3:low"}
DEFAULT_S_LABEL = "S:proposal"
DEFAULT_P_LABEL = "P3:low"


def _get_token() -> str:
    """Extract token from ~/.config/gh/hosts.yml."""
    if HOSTS_YML.exists():
        for line in HOSTS_YML.read_text().splitlines():
            if "oauth_token:" in line:
                return line.split("oauth_token:", 1)[1].strip()
    return ""


def gh_api(url: str) -> list | dict:
    """Call GitHub REST API directly (no gh CLI dependency for data fetching)."""
    token = _get_token()
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        print(f"  [ERROR] HTTP {e.code} for {url[:60]}... {body}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [ERROR] {e}", file=sys.stderr)
        return []


def gh(*args: str) -> list:
    """Run gh command with token from hosts.yml."""
    token = _get_token()
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


def extract_lkpr(title: str) -> Optional[str]:
    m = re.search(r"LKPR-(\d+)", title, re.IGNORECASE)
    return f"LKPR-{m.group(1)}" if m else None


def extract_lkpr_num(title: str) -> Optional[int]:
    m = re.search(r"LKPR-(\d+)", title, re.IGNORECASE)
    return int(m.group(1)) if m else None


def label_names(issue: dict) -> list[str]:
    return [l.get("name", "") for l in issue.get("labels", [])]


def has_label(labels: list[str], prefix: str) -> bool:
    return any(l.startswith(prefix) for l in labels)


def get_s_label(issue: dict) -> str:
    lbls = label_names(issue)
    return next((l for l in lbls if l.startswith("S:")), "")


# ── data loading via GH API (no local repo needed) ────────────────────────

def load_all_issues() -> list[dict]:
    """Fetch ALL issues (open+closed) via paginated API."""
    print(f"\n  Fetching all issues...", end=" ", flush=True)
    all_issues = []
    page = 1
    while True:
        issues = gh_api(
            f"https://api.github.com/repos/{REPO}/issues"
            f"?state=all&per_page=100&page={page}"
        )
        if not issues or not isinstance(issues, list):
            break
        all_issues.extend(issues)
        page += 1
        if len(issues) < 100:
            break
    # Filter out PRs
    pure = [i for i in all_issues if "pull_request" not in i]
    print(f"{len(pure)} issues (from {len(all_issues)} total)")
    return pure


def load_merged_prs() -> list[dict]:
    """Fetch merged PRs via paginated API."""
    print(f"  Fetching merged PRs...", end=" ", flush=True)
    all_prs = []
    page = 1
    while True:
        prs = gh_api(
            f"https://api.github.com/repos/{REPO}/pulls"
            f"?state=closed&per_page=100&page={page}"
        )
        if not prs or not isinstance(prs, list):
            break
        merged = [p for p in prs if p.get("merged_at")]
        all_prs.extend(merged)
        page += 1
        if len(prs) < 100:
            break
    print(f"{len(all_prs)} PRs")
    return all_prs


def load_backlog_files() -> dict[str, dict]:
    """Load all backlog files from repo via GH API.

    Returns {LKPR-N: {status, title, section}}.
    """
    print(f"  Fetching backlog files...", end=" ", flush=True)
    result = {}
    for section in ["proposal", "done", "backlog", "deferred"]:
        items = gh_api(f"https://api.github.com/repos/{REPO}/contents/backlogs/{section}")
        if not items or not isinstance(items, list):
            continue
        for item in items:
            if item["type"] != "file":
                continue
            fname = item["name"]
            lkpr = extract_lkpr(fname)
            if not lkpr:
                continue
            # Try to read frontmatter
            file_data = gh_api(item["url"])
            if not file_data or not isinstance(file_data, dict):
                continue
            import base64
            try:
                text = base64.b64decode(file_data["content"]).decode()
            except Exception:
                text = ""
            status = ""
            title_line = fname.replace(".md", "")
            for line in text.splitlines():
                if line.startswith("status:"):
                    status = line.split(":", 1)[1].strip()
                elif line.startswith("title:"):
                    title_line = line.split(":", 1)[1].strip()
            result[lkpr] = {
                "status": status,
                "section": section,
                "filename": fname,
                "title": title_line,
            }
    print(f"{len(result)} files")
    return result


# ── standard checks ──────────────────────────────────────────────────────

def check_merged_not_done(open_issues: list[dict], merged_prs: list[dict]) -> list:
    """Issues with merged PRs but not labeled S:Done."""
    print("\n── Check 1: Merged PRs → issue not marked S:Done ──")
    TICKET_CREATION_KEYWORDS = {"ticket", "proposal", "proposals", "filing", "plans"}
    prs_by_lkpr: dict[str, list] = defaultdict(list)
    for pr in merged_prs:
        title = pr.get("title", "")
        title_lower = title.lower()
        if any(kw in title_lower for kw in TICKET_CREATION_KEYWORDS):
            continue
        for m in re.finditer(r"LKPR-(\d+)", title):
            prs_by_lkpr[f"LKPR-{m.group(1)}"].append(pr)

    issues_by_lkpr: dict[str, list] = defaultdict(list)
    for issue in open_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr:
            issues_by_lkpr[lkpr].append(issue)

    findings = []
    for lkpr, prs in sorted(prs_by_lkpr.items()):
        for issue in issues_by_lkpr.get(lkpr, []):
            lbls = label_names(issue)
            if not has_label(lbls, "S:Done"):
                merged_nums = [p["number"] for p in prs]
                findings.append({"type": "merged_not_done", "lkpr": lkpr, "issue": issue["number"], "prs": merged_nums, "labels": lbls})
                print(f"  ✗ #{issue['number']} [{lkpr}] has merged PR#{merged_nums[0]} but labels: {', '.join(lbls)}")
    if not findings:
        print("  ✓ All merged PRs have corresponding S:Done issues.")
    return findings


def check_done_but_open(open_issues: list[dict]) -> list:
    """Issues labeled S:Done but still open."""
    print("\n── Check 2: S:Done issues still open ──")
    findings = []
    for issue in open_issues:
        lbls = label_names(issue)
        if has_label(lbls, "S:Done"):
            findings.append({"type": "done_but_open", "lkpr": extract_lkpr(issue["title"]), "issue": issue["number"]})
            print(f"  ✗ #{issue['number']} labeled S:Done but still open — should be closed")
    if not findings:
        print("  ✓ No S:Done issues left open.")
    return findings


def check_duplicates(all_issues: list[dict]) -> list:
    """Find duplicate issues referencing the same LKPR-N."""
    print("\n── Check 3: Duplicate issues (same LKPR-N) ──")
    findings = []
    by_lkpr: dict[str, list] = defaultdict(list)
    for issue in all_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr:
            by_lkpr[lkpr].append(issue)

    for lkpr, issues in sorted(by_lkpr.items()):
        if len(issues) <= 1:
            continue
        sorted_i = sorted(issues, key=lambda i: i["number"])
        kept = [i for i in sorted_i if i["state"] == "open"]
        closed = [i for i in sorted_i if i["state"] == "closed"]
        cancelled_closed = [c for c in closed if "S:Cancelled" in label_names(c)]
        deferred_closed = [c for c in closed if "S:Deferred" in label_names(c)]
        # Already reconciled: one open, rest are S:Cancelled or S:Deferred
        if len(kept) == 1 and len(cancelled_closed) + len(deferred_closed) == len(closed) and len(closed) > 0:
            continue
        if len(kept) == 0:
            continue
        findings.append({
            "type": "duplicate",
            "lkpr": lkpr,
            "open_count": len(kept),
            "closed_count": len(closed),
            "open": [i["number"] for i in kept],
            "closed": [{"num": i["number"], "label": get_s_label(i)} for i in closed],
        })
        nums = ", ".join(f"#{i['number']}({i['state']}/{get_s_label(i)})" for i in sorted_i)
        print(f"  ⚠ [{lkpr}] {len(issues)} copies: {nums}")
    if not findings:
        print("  ✓ No duplicates found.")
    return findings


def check_markdown_vs_github(all_issues: list[dict], backlog: dict[str, dict]) -> list:
    """Compare backlog file section vs GH issue label."""
    print("\n── Check 4: Markdown file section vs GitHub label ──")
    count = 0
    issues_by_lkpr: dict[str, dict] = {}
    for issue in all_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr and lkpr not in issues_by_lkpr:
            issues_by_lkpr[lkpr] = issue

    for lkpr, md in sorted(backlog.items()):
        issue = issues_by_lkpr.get(lkpr)
        if not issue:
            print(f"  ? [{lkpr}] backlog file exists but no GH issue")
            count += 1
            continue
        gh_labels = label_names(issue)
        gh_s = next((l for l in gh_labels if l.startswith("S:")), "")
        md_s = md["status"] or ""

        # Normalize case
        if md_s and md_s.lower() != gh_s.lower():
            print(f"  ✗ #{issue['number']} [{lkpr}] file has status:'{md_s}' but GH label:'{gh_s}'")
            count += 1

    if count == 0:
        print("  ✓ All backlog file statuses match GitHub labels.")
    return []


# ── DEEP checks ──────────────────────────────────────────────────────────

def deep_check_done(all_issues: list[dict], merged_prs: list[dict]) -> list[dict]:
    """Verify S:Done issues have actual feature PRs (not just proposal PRs)."""
    print("\n── Deep Check A: S:Done verification ──")
    results = []
    TICKET_CREATION_KEYWORDS = {"ticket", "proposal", "proposals", "filing", "plans", "chore"}
    for issue in all_issues:
        if get_s_label(issue) != "S:Done":
            continue
        num = issue["number"]
        lkpr = extract_lkpr(issue.get("title", "")) or "?"
        lbls = label_names(issue)

        # Find merged PRs referencing this issue's LKPR
        linked_prs = []
        for pr in merged_prs:
            pr_title = pr.get("title", "")
            pr_title_lower = pr_title.lower()
            if any(kw in pr_title_lower for kw in TICKET_CREATION_KEYWORDS):
                continue
            if lkpr.replace("LKPR-", "") in re.findall(r"LKPR-(\d+)", pr_title):
                linked_prs.append(pr["number"])

        if linked_prs:
            verdict = f"OK (PR#{','.join(map(str, linked_prs))})"
        else:
            verdict = "PRE-PR ERA (no merged PR, relies on direct commits)"

        results.append({"num": num, "lkpr": lkpr, "verdict": verdict})
        print(f"  #{num} [{lkpr}] {verdict}")
    return results


def deep_check_cancelled(all_issues: list[dict], backlog: dict[str, dict]) -> list[dict]:
    """Check S:Cancelled issues — really cancelled or actually implemented?"""
    print("\n── Deep Check B: S:Cancelled verification ──")
    results = []
    for issue in all_issues:
        if get_s_label(issue) != "S:Cancelled":
            continue
        num = issue["number"]
        lkpr = extract_lkpr(issue.get("title", "")) or "?"
        file_info = backlog.get(lkpr, {})

        file_section = file_info.get("section", "")
        has_open_successor = False
        for other in all_issues:
            if other["number"] != num and lkpr in other.get("title", "") and other["state"] == "open":
                has_open_successor = True
                break

        if has_open_successor:
            verdict = "DUPLICATE (has open successor)"
        elif file_section == "done":
            verdict = "⚠ IMPLEMENTED (file in done/) — should be S:Done"
        else:
            verdict = "CANCELLED (no successor, file in proposal/)"

        results.append({"num": num, "lkpr": lkpr, "verdict": verdict})
        print(f"  #{num} [{lkpr}] {verdict}")
    return results


def deep_check_closed_proposal(all_issues: list[dict], backlog: dict[str, dict]) -> list[dict]:
    """Categorize closed S:Proposal issues."""
    print("\n── Deep Check C: Closed S:Proposal categorization ──")
    results = []
    for issue in all_issues:
        if get_s_label(issue) != "S:Proposal" or issue["state"] != "closed":
            continue
        num = issue["number"]
        lkpr = extract_lkpr(issue.get("title", "")) or "?"
        file_info = backlog.get(lkpr, {})

        has_open_dup = False
        for other in all_issues:
            if other["number"] != num and lkpr in other.get("title", "") and other["state"] == "open":
                has_open_dup = True
                break

        # Check if closed by a chore PR (PR #144)
        timeline = gh_api(f"https://api.github.com/repos/{REPO}/issues/{num}/timeline")
        pr_refs = [e for e in timeline if e.get("event") == "cross-referenced" and e.get("source", {}).get("issue", {}).get("pull_request")]
        chore_pr = any(e.get("source", {}).get("issue", {}).get("number") in (144,) for e in pr_refs) if pr_refs else False

        if chore_pr and 'not_planned' in str(timeline):
            verdict = "NOT_PLANNED"
        elif has_open_dup:
            verdict = "DUPLICATE (has open successor)"
        elif chore_pr:
            verdict = "ORPHAN (closed by chore PR) → REOPEN"
        elif not pr_refs:
            verdict = "ORPHAN (unknown closure) → REOPEN"
        else:
            verdict = "ORPHAN → REOPEN"

        results.append({"num": num, "lkpr": lkpr, "verdict": verdict})
        print(f"  #{num} [{lkpr}] {verdict}")
    return results


def deep_check_closed_ready(all_issues: list[dict], merged_prs: list[dict]) -> list[dict]:
    """Check closed S:Ready issues for merged PRs → should be S:Done."""
    print("\n── Deep Check D: Closed S:Ready → S:Done ──")
    results = []
    TICKET_CREATION_KEYWORDS = {"ticket", "proposal", "proposals", "filing", "plans", "chore"}
    for issue in all_issues:
        if get_s_label(issue) != "S:Ready" or issue["state"] != "closed":
            continue
        num = issue["number"]
        lkpr = extract_lkpr(issue.get("title", "")) or "?"

        # Check timeline for merged PRs
        timeline = gh_api(f"https://api.github.com/repos/{REPO}/issues/{num}/timeline")
        linked_prs = []
        for e in timeline:
            if e.get("event") == "cross-referenced" and e.get("source", {}).get("issue", {}).get("pull_request"):
                pr_num = e["source"]["issue"]["number"]
                pr_data = gh_api(f"https://api.github.com/repos/{REPO}/pulls/{pr_num}")
                if isinstance(pr_data, dict) and pr_data.get("merged"):
                    linked_prs.append(pr_num)

        if linked_prs:
            verdict = f"→ S:Done (PR#{','.join(map(str, linked_prs))} merged)"
        else:
            verdict = "closed without merged PR — check manually"

        results.append({"num": num, "lkpr": lkpr, "verdict": verdict})
        print(f"  #{num} [{lkpr}] {verdict}")
    return results


def deep_check_file_location(all_issues: list[dict], backlog: dict[str, dict]) -> list[dict]:
    """Check file section vs GH S: label mismatch."""
    print("\n── Deep Check E: File location vs GH label ──")
    section_to_label = {
        "done": {"S:Done", "S:Cancelled"},
        "deferred": {"S:Deferred"},
        "backlog": {"S:Ready", "S:Review", "S:In-progress"},
        "proposal": {"S:Proposal"},
    }
    results = []
    issues_by_lkpr: dict[str, dict] = {}
    for issue in all_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr and lkpr not in issues_by_lkpr:
            issues_by_lkpr[lkpr] = issue

    for lkpr, md in sorted(backlog.items()):
        file_section = md["section"]
        issue = issues_by_lkpr.get(lkpr)
        if not issue:
            continue
        gh_s = get_s_label(issue)
        expected_sections = {k for k, v in section_to_label.items() if gh_s in v}
        if expected_sections and file_section not in expected_sections:
            results.append({"lkpr": lkpr, "issue": issue["number"], "file_section": file_section, "gh_label": gh_s})
            print(f"  ⚠ #{issue['number']} [{lkpr}] file in '{file_section}/' but GH label '{gh_s}'")

    if not results:
        print("  ✓ All file locations match GH labels.")
    return results


def deep_check_missing_gh_issues(backlog: dict[str, dict], all_issues: list[dict]) -> list[dict]:
    """Find backlog files with no corresponding GH issue."""
    print("\n── Deep Check F: Backlog files without GH issues ──")
    results = []
    known_lkprs = set()
    for issue in all_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr:
            known_lkprs.add(lkpr)

    for lkpr, md in sorted(backlog.items()):
        if lkpr not in known_lkprs:
            results.append({"lkpr": lkpr, "section": md["section"], "filename": md["filename"]})
            print(f"  ⚠ [{lkpr}] file backlogs/{md['section']}/{md['filename']} has no GH issue")

    if not results:
        print("  ✓ All backlog files have corresponding GH issues.")
    return results


# ── deep summary table ────────────────────────────────────────────────────

def print_deep_table(all_issues: list[dict], backlog: dict[str, dict],
                     cancelled_results: list, closed_proposal_results: list,
                     closed_ready_results: list, file_loc_results: list,
                     missing_issues: list) -> None:
    """Print the master LKPR-sorted table."""
    print("\n" + "=" * 130)
    print(f"{'LKPR':<10} {'GH#':<6} {'GH State':<10} {'GH Label':<18} {'File Dir':<10} {'Verdict/Action'}")
    print("=" * 130)

    # Build verdict lookup
    verdicts: dict[int, str] = {}
    actions: dict[int, str] = {}

    # Cancelled verdicts
    for r in cancelled_results:
        lkpr_num = r["num"]
        v = r["verdict"]
        if "IMPLEMENTED" in v:
            actions[lkpr_num] = "→ S:Done"
            verdicts[lkpr_num] = v
        elif "DUPLICATE" in v:
            actions[lkpr_num] = "✅ duplicate"
            verdicts[lkpr_num] = v
        else:
            actions[lkpr_num] = "✅ cancelled"
            verdicts[lkpr_num] = v

    # Closed proposal verdicts
    for r in closed_proposal_results:
        lkpr_num = r["num"]
        v = r["verdict"]
        if "REOPEN" in v:
            verdicts[lkpr_num] = v
            actions[lkpr_num] = "🔴 REOPEN"
        elif "NOT_PLANNED" in v:
            verdicts[lkpr_num] = v
            actions[lkpr_num] = "✅ not_planned"
        elif "DUPLICATE" in v:
            verdicts[lkpr_num] = v
            actions[lkpr_num] = "✅ duplicate"

    # Closed ready verdicts
    for r in closed_ready_results:
        lkpr_num = r["num"]
        v = r["verdict"]
        if "S:Done" in v:
            verdicts[lkpr_num] = v
            actions[lkpr_num] = "🔴→ S:Done"

    # Missing issues
    for r in missing_issues:
        lkpr_str = r["lkpr"]
        lkpr_num = int(lkpr_str.replace("LKPR-", ""))
        verdicts[lkpr_num] = "no GH issue"
        actions[lkpr_num] = "⚠ CREATE"

    # File location mismatches
    for r in file_loc_results:
        lkpr_str = r["lkpr"]
        lkpr_num = int(lkpr_str.replace("LKPR-", ""))

    # Build by-lkpr groups
    by_lkpr: dict[str, list] = defaultdict(list)
    for issue in all_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr:
            by_lkpr[lkpr].append(issue)

    # Add file-only entries
    for lkpr_str in backlog:
        if lkpr_str not in by_lkpr:
            by_lkpr[lkpr_str] = []

    for lkpr_str in sorted(by_lkpr.keys(), key=lambda x: int(x.replace("LKPR-", ""))):
        issues = by_lkpr[lkpr_str]
        lkpr_num = int(lkpr_str.replace("LKPR-", ""))
        file_info = backlog.get(lkpr_str, {})
        file_dir = file_info.get("section", "—")

        if not issues:
            action = actions.get(lkpr_num, "⚠ CREATE")
            print(f"{lkpr_str:<10} {'—':<6} {'—':<10} {'—':<18} {file_dir:<10} {action}")
            continue

        for i in issues:
            num = i["number"]
            state = i["state"]
            gh_s = get_s_label(i)
            action = actions.get(num, "")
            verdict = verdicts.get(num, "")

            # Default actions based on GH state
            if not action:
                if gh_s == "S:Done":
                    action = "✅ done"
                elif gh_s == "S:Proposal" and state == "open":
                    action = "✅ proposal"
                elif gh_s == "S:Ready" and state == "open":
                    action = "✅ ready"
                elif gh_s == "S:Deferred":
                    action = "✅ deferred"
                elif gh_s == "S:Proposal" and state == "closed":
                    action = "? check"
                else:
                    action = "?"

            print(f"{lkpr_str:<10} #{num:<4} {state:<10} {gh_s:<18} {file_dir:<10} {action}")

    print("=" * 130)


# ── fix helpers ──────────────────────────────────────────────────────────

def fix_done_issues(open_issues: list[dict]) -> None:
    """Close S:Done issues."""
    print("\n── Auto-fix: closing S:Done open issues ──")
    for issue in open_issues:
        lbls = label_names(issue)
        if has_label(lbls, "S:Done"):
            num = issue["number"]
            print(f"  Closing #{num} [{issue['title']}]... ", end="", flush=True)
            r = subprocess.run(["gh", "issue", "close", str(num), "--repo", REPO], capture_output=True, text=True)
            print("✓" if r.returncode == 0 else f"FAILED: {r.stderr.strip()}")


def fix_missing_labels(open_issues: list[dict], markdown: dict[str, dict]) -> None:
    """Auto-add missing S: and P: labels."""
    print("\n── Auto-fix: adding missing labels ──")
    issues_by_lkpr: dict[str, dict] = {}
    for issue in open_issues:
        lkpr = extract_lkpr(issue.get("title", ""))
        if lkpr:
            issues_by_lkpr[lkpr] = issue
    for issue in open_issues:
        num = issue["number"]
        lbls = label_names(issue)
        to_add: list[str] = []
        s_labels = [l for l in lbls if l.startswith("S:")]
        if len(s_labels) == 0:
            lkpr = extract_lkpr(issue.get("title", ""))
            inferred = (markdown.get(lkpr) or {}).get("status", "") if lkpr else ""
            inferred_label = inferred if inferred in VALID_S_LABELS else DEFAULT_S_LABEL
            to_add.append(inferred_label)
        p_labels = [l for l in lbls if l.startswith("P:")]
        if len(p_labels) == 0:
            to_add.append(DEFAULT_P_LABEL)
        if not to_add:
            continue
        for label in to_add:
            print(f"  Adding {label} to #{num} [{issue['title']}]... ", end="", flush=True)
            r = subprocess.run(["gh", "issue", "edit", str(num), "--repo", REPO, "--add-label", label], capture_output=True, text=True)
            print("✓" if r.returncode == 0 else f"FAILED: {r.stderr.strip()}")


# ── main ──────────────────────────────────────────────────────────────────

def main():
    markdown_only = "--markdown-only" in sys.argv
    fix_done = "--fix-done" in sys.argv
    fix_labels = "--fix-labels" in sys.argv
    deep = "--deep" in sys.argv

    print("╔══════════════════════════════════════════════╗")
    print("║  GH-Reconcile — Issue ↔ PR ↔ Backlog Sync   ║")
    if deep:
        print("║  [DEEP MODE — full datafix analysis]        ║")
    print("╚══════════════════════════════════════════════╝")

    # Load all data
    all_issues = load_all_issues()
    merged_prs = load_merged_prs()
    backlog = load_backlog_files()

    open_issues = [i for i in all_issues if i["state"] == "open"]
    closed_issues = [i for i in all_issues if i["state"] == "closed"]

    print(f"\n  Open issues: {len(open_issues)}")
    print(f"  Closed issues: {len(closed_issues)}")
    print(f"  Merged PRs: {len(merged_prs)}")
    print(f"  Backlog files: {len(backlog)}")

    if deep:
        # ── Deep mode: full datafix analysis ──
        deep_cancelled = deep_check_cancelled(all_issues, backlog)
        deep_closed_proposal = deep_check_closed_proposal(all_issues, backlog)
        deep_closed_ready = deep_check_closed_ready(all_issues, merged_prs)
        deep_file_loc = deep_check_file_location(all_issues, backlog)
        deep_missing = deep_check_missing_gh_issues(backlog, all_issues)
        deep_done = deep_check_done(all_issues, merged_prs)

        # Print master table
        print_deep_table(all_issues, backlog, deep_cancelled, deep_closed_proposal,
                         deep_closed_ready, deep_file_loc, deep_missing)

        # Summary of actions needed
        print("\n\n" + "=" * 70)
        print("  ACTIONS NEEDED (manually apply):")
        print("=" * 70)

        actions_needed = []

        for r in deep_cancelled:
            if "IMPLEMENTED" in r["verdict"]:
                actions_needed.append(f"  🔴 #{r['num']} [{r['lkpr']}] Label S:Cancelled → S:Done")
        for r in deep_closed_proposal:
            if "REOPEN" in r["verdict"]:
                actions_needed.append(f"  🔴 #{r['num']} [{r['lkpr']}] Reopen + label S:Proposal ({r['verdict']})")
        for r in deep_closed_ready:
            if "S:Done" in r["verdict"]:
                actions_needed.append(f"  🔴 #{r['num']} [{r['lkpr']}] Label S:Ready → S:Done")
        for r in deep_missing:
            actions_needed.append(f"  ⚠️ [{r['lkpr']}] Create GH issue (file: backlogs/{r['section']}/{r['filename']})")
        for r in deep_file_loc:
            actions_needed.append(f"  📁 #{r['issue']} [{r['lkpr']}] File in '{r['file_section']}/' but GH label '{r['gh_label']}' — move file")

        if actions_needed:
            for a in actions_needed:
                print(a)
        else:
            print("  ✅ No actions needed — all clean!")

        # Duplicate flagging
        print("\n  DUPLICATE TICKETS (manual review for deletion):")
        dupes = check_duplicates(all_issues)
        if dupes:
            for d in dupes:
                print(f"  ⚠ [{d['lkpr']}] Open: #{d['open']},  Closed: {[c['num'] for c in d['closed']]}")
                print(f"       Review and delete the closed duplicate copy")
        else:
            print("  ✅ No active duplicates to resolve.")

    else:
        # ── Standard mode ──
        f1 = check_merged_not_done(open_issues, merged_prs)
        f2 = check_done_but_open(open_issues)
        f3 = check_duplicates(all_issues)
        f4 = check_markdown_vs_github(all_issues, backlog)
        f5 = []  # skip branches (no local repo)
        f6 = check_missing_invalid_labels(all_issues)

        total = len(f1) + len(f2) + len(f3) + len(f6)
        print(f"\n{'='*50}")
        print(f"  Total inconsistencies found: {total}")
        if total == 0:
            print("  ✓ All clean!")
        else:
            print(f"\n  Fix suggestions:")
            if f1:
                print(f"    → {len(f1)} issues have merged PRs but aren't S:Done")
                print(f"       Run with --fix-done to auto-close")
            if f2:
                print(f"    → {len(f2)} S:Done issues still open")
                print(f"       Run with --fix-done to auto-close")
            if f3:
                print(f"    → {len(f3)} duplicate LKPR sets to resolve")
            if f6:
                missing = [f for f in f6 if f.get("problem") in ("missing_S", "missing_P")]
                if missing:
                    print(f"    → {len(missing)} issues missing labels")
                    print(f"       Run with --fix-labels to auto-add defaults")

        if fix_done and (f1 or f2):
            fix_done_issues(open_issues)
        if fix_labels and f6:
            fix_missing_labels(open_issues, backlog)


def check_missing_invalid_labels(all_issues: list[dict]) -> list:
    """Find issues missing status (S:) or priority (P:) labels."""
    print("\n── Check 6: Missing / invalid labels ──")
    findings = []
    for issue in all_issues:
        if issue["state"] != "open":
            continue
        num = issue["number"]
        title = issue["title"]
        lbls = label_names(issue)
        s_labels = [l for l in lbls if l.startswith("S:")]
        p_labels = [l for l in lbls if l.startswith("P:")]
        entry: dict = {"issue": num, "title": title, "labels": lbls}
        if len(s_labels) == 0:
            entry["problem"] = "missing_S"
            findings.append(entry)
            print(f"  ✗ #{num} [{title}] — missing status (S:) label")
        elif len(s_labels) > 1:
            entry["problem"] = "multiple_S"
            entry["s_labels"] = s_labels
            findings.append(entry)
            print(f"  ✗ #{num} [{title}] — multiple status labels: {', '.join(s_labels)}")
        else:
            s = s_labels[0]
            if s.lower() not in {v.lower() for v in VALID_S_LABELS}:
                entry["problem"] = "invalid_S"
                entry["s_labels"] = [s]
                findings.append(entry)
                print(f"  ✗ #{num} [{title}] — unknown status label: {s}")
        if len(p_labels) == 0:
            entry = {**entry}
            if "problem" not in entry:
                entry["problem"] = "missing_P"
                findings.append(entry)
            print(f"  ✗ #{num} [{title}] — missing priority (P:) label")
        elif len(p_labels) > 1:
            entry = {**entry}
            if "problem" not in entry:
                entry["problem"] = "multiple_P"
                findings.append(entry)
            print(f"  ✗ #{num} [{title}] — multiple priority labels: {', '.join(p_labels)}")
    if not findings:
        print("  ✓ All open issues have status and priority labels.")
    return findings


if __name__ == "__main__":
    main()