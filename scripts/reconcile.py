#!/usr/bin/env python3
"""
Reconcile ticket files ↔ GitHub issues ↔ PRs.

Validates:

  Ticket -> Issue:
    - Every ticket must reference exactly 1 GitHub issue
    - The issue must exist

  Issue -> PR -> Label:
    1. Merged feature PR (non-proposal branch) -> label S:Done
    2. Merged proposal PR only -> label S:Proposal
    3. Issue closed (not_planned) -> label S:Cancelled
    4. No PR -> label S:Proposal

  File location:
    1. S:Done -> backlogs/done/
    2. S:Cancelled -> backlogs/cancelled/
    3. S:Proposal -> backlogs/proposal/

Exit 0 -- all consistent.
Exit 1 -- issues found.
With --fix, auto-moves files and updates labels.

Usage:
    uv run python scripts/reconcile.py          # check only
    uv run python scripts/reconcile.py --fix    # auto-fix
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
GITHUB_REPO = "Jessinra/Lorekeeper"

# Maps GH label (as-is) -> expected directory
STATUS_DIR: dict[str, Path] = {
    "S:Done": ROOT / "backlogs" / "done",
    "S:Cancelled": ROOT / "backlogs" / "cancelled",
    "S:Proposal": ROOT / "backlogs" / "proposal",
    "S:In-progress": ROOT / "backlogs" / "backlog",
    "S:Ready": ROOT / "backlogs" / "backlog",
    "S:Review": ROOT / "backlogs" / "backlog",
}

# Valid status labels per directory
DIR_VALID_STATUSES: dict[str, set[str]] = {
    "proposal": {"S:Proposal"},
    "done": {"S:Done"},
    "cancelled": {"S:Cancelled"},
    "backlog": {"S:In-progress", "S:Ready", "S:Review"},
}


def _get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    c = Path.home() / ".config" / "gh" / "hosts.yml"
    if c.exists():
        m = re.search(r"oauth_token:\s*(\S+)", c.read_text())
        if m:
            return m.group(1)
    return ""


def _api(path: str, token: str) -> dict | list | None:
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "lorekeeper-reconcile",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError:
        return None


def _paginate(path: str, token: str, max_pages: int = 5) -> list[dict]:
    results: list[dict] = []
    page = 1
    while page <= max_pages:
        sep = "&" if "?" in path else "?"
        d = _api(f"{path}{sep}per_page=100&page={page}", token)
        if not d or not isinstance(d, list):
            break
        results.extend(d)
        if len(d) < 100:
            break
        page += 1
    return results


def extract_frontmatter_field(text: str, field: str) -> str | None:
    m = re.search(rf"^{field}:\s*(.+?)\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def fetch_all_prs(token: str) -> dict[int, dict]:
    """Fetch all merged PRs, map by LKPR-N extracted from title.

    PR titles follow pattern: [LKPR-N] ... or LKPR-N: ...
    Returns {issue_number: {"pr": N, "branch": "...", "is_proposal": bool, ...}}
    """
    from collections import defaultdict

    # First pass: collect PRs by LKPR-N from title
    lkpr_to_prs: dict[str, list[dict]] = defaultdict(list)
    prs = _paginate(
        f"/repos/{GITHUB_REPO}/pulls?state=closed&sort=updated&direction=desc",
        token,
        max_pages=10,
    )
    for pr in prs:
        if not pr.get("merged_at"):
            continue
        title = pr.get("title", "")
        m = re.search(r"\[?LKPR-(\d+)\]?", title, re.IGNORECASE)
        if not m:
            continue
        lkpr_num = m.group(1)  # e.g. "67"
        lkpr_to_prs[lkpr_num].append({
            "pr": pr["number"],
            "branch": pr["head"]["ref"],
            "is_proposal": pr["head"]["ref"].startswith("proposal/"),
            "merged_at": pr.get("merged_at", ""),
            "title": title,
        })

    # We can't map LKPR-N to GitHub issue number without reading files.
    # Return the LKPR-indexed map; we'll look it up by ticket ID later.
    return lkpr_to_prs  # type: ignore[return-value]


def fetch_issue_labels_batch(token: str) -> dict[int, list[str]]:
    """Fetch labels for all open issues at once (paginate labels endpoint)."""
    result: dict[int, list[str]] = {}
    issues = _paginate(
        f"/repos/{GITHUB_REPO}/issues?state=all&sort=updated&direction=desc",
        token,
        max_pages=10,
    )
    for issue in issues:
        if "pull_request" in issue:
            continue  # skip PRs
        num = issue["number"]
        result[num] = [label["name"] for label in issue.get("labels", [])]
        result[f"_{num}_state"] = issue.get("state")  # type: ignore[assignment]
        result[f"_{num}_reason"] = issue.get("state_reason")  # type: ignore[assignment]
    return result


def _expected_status(
    issue_state: str | None,
    state_reason: str | None,
    prs_for_ticket: list[dict],
) -> str:
    """Determine expected GH label based on PRs and issue state."""
    if issue_state == "closed" and state_reason == "not_planned":
        return "S:Cancelled"
    if not prs_for_ticket:
        return "S:Proposal"
    # Most recent merged PR determines the status
    latest = max(prs_for_ticket, key=lambda p: p.get("merged_at", ""))
    if latest["is_proposal"]:
        return "S:Proposal"
    return "S:Done"


def main() -> int:
    token = _get_token()
    if not token:
        print("No GitHub token available.")
        return 1

    do_fix = "--fix" in sys.argv
    errors = 0
    warnings = 0
    fixes = 0

    # Scan all ticket files
    tickets: list[tuple[Path, str, str, int | None]] = []
    for subdir in ["proposal", "done", "cancelled", "backlog"]:
        dp = ROOT / "backlogs" / subdir
        if not dp.exists():
            continue
        for fp in sorted(dp.glob("*.md")):
            text = fp.read_text()
            fm = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            gi_raw = extract_frontmatter_field(fm.group(1), "github_issue")
            tid = extract_frontmatter_field(fm.group(1), "id") or fp.name.split("-")[0]
            issue_num = int(gi_raw) if gi_raw and gi_raw.isdigit() else None
            tickets.append((fp, tid, subdir, issue_num))

    print(f"{len(tickets)} ticket files found.")

    # Batch fetch all merged PRs
    print("Fetching merged PRs...", end=" ", flush=True)
    all_prs = fetch_all_prs(token)
    # Flatten to {issue_number -> [PRs]} by matching ticket id
    ticket_prs: dict[int, list[dict]] = {}
    for _fp, tid, _subdir, issue_num in tickets:
        if issue_num is None:
            continue
        # Find PRs for this ticket by LKPR-N in ticket id
        lkpr_match = re.search(r"LKPR-(\d+)", tid, re.IGNORECASE)
        if not lkpr_match:
            continue
        lkpr_key = lkpr_match.group(1)
        prs = all_prs.get(lkpr_key, [])
        if prs:
            ticket_prs[issue_num] = prs

    print(f"{sum(len(v) for v in all_prs.values())} PRs found.")

    # Batch fetch issue labels
    print("Fetching issue labels...", end=" ", flush=True)
    issue_data = fetch_issue_labels_batch(token)
    # Reorganize
    issue_labels: dict[int, list[str]] = {}
    issue_states: dict[int, str] = {}
    issue_reasons: dict[int, str | None] = {}
    for k, v in issue_data.items():
        if isinstance(k, int):
            issue_labels[k] = v  # type: ignore[assignment]
            issue_states[k] = issue_data.get(f"_{k}_state", "")  # type: ignore[assignment]
            issue_reasons[k] = issue_data.get(f"_{k}_reason", None)  # type: ignore[assignment]

    print(f"{len(issue_labels)} issues loaded.\n")

    # Process each ticket
    for filepath, ticket_id, cur_dir, issue_num in tickets:
        if issue_num is None:
            continue

        ctx = f"{ticket_id} (#{issue_num}) [{cur_dir}]"
        labels = issue_labels.get(issue_num, [])
        issue_state = issue_states.get(issue_num, "unknown")
        state_reason = issue_reasons.get(issue_num, None)

        status_labels = [s for s in labels if s.startswith("S:")]
        current_status = status_labels[0] if status_labels else None

        if not current_status:
            warnings += 1
            print(f"  W {ctx}: no S:* label (labels: {labels})")
            continue

        # --- Check file location ---
        exp_dir = STATUS_DIR.get(current_status)
        if exp_dir and filepath.parent != exp_dir:
            print(
                f"  X {ctx}: in backlogs/{cur_dir}/ but label is '{current_status}'"
                f" (belongs in backlogs/{exp_dir.name}/)"
            )
            errors += 1
            if do_fix:
                dst = exp_dir / filepath.name
                if dst.exists():
                    dst = exp_dir / f"{filepath.stem}-reconciled{filepath.suffix}"
                shutil.move(str(filepath), str(dst))
                print(f"    -> moved to {dst.parent.name}/")
                os.system(
                    f"cd {ROOT} && git rm --quiet {filepath} 2>/dev/null || true"
                )
                fixes += 1

        # --- Check status validity for directory ---
        valid = DIR_VALID_STATUSES.get(cur_dir, set())
        if cur_dir not in ("cancelled",) and valid and current_status not in valid:
            print(f"  W {ctx}: '{current_status}' not valid for backlogs/{cur_dir}/")
            warnings += 1

        # --- Determine expected status from PRs ---
        prs_for_ticket = ticket_prs.get(issue_num, [])
        expected = _expected_status(issue_state, state_reason, prs_for_ticket)

        if current_status != expected:
            if current_status == "S:Proposal" and expected == "S:Proposal":
                continue
            pr_detail = (
                f"PR #{prs_for_ticket[0]['pr']} ({prs_for_ticket[0]['branch']})"
                if prs_for_ticket
                else "no PR"
            )
            print(
                f"  W {ctx}: label '{current_status}' but expected"
                f" '{expected}' ({pr_detail})"
            )
            warnings += 1

            if do_fix:
                del_url = (
                    f"https://api.github.com/repos/{GITHUB_REPO}"
                    f"/issues/{issue_num}/labels/{current_status}"
                )
                del_req = urllib.request.Request(
                    del_url,
                    headers={
                        "Authorization": f"token {token}",
                        "User-Agent": "lorekeeper-reconcile",
                    },
                    method="DELETE",
                )
                try:
                    urllib.request.urlopen(del_req)
                except urllib.error.HTTPError:
                    pass

                add_body = json.dumps({"labels": [expected]}).encode()
                add_url = (
                    f"https://api.github.com/repos/{GITHUB_REPO}"
                    f"/issues/{issue_num}/labels"
                )
                add_req = urllib.request.Request(
                    add_url,
                    data=add_body,
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                try:
                    urllib.request.urlopen(add_req)
                    print(f"    -> label updated to '{expected}' on #{issue_num}")
                    fixes += 1
                except urllib.error.HTTPError as e:
                    print(f"    -> label update failed: {e}")

    print()
    if errors:
        print(f"{errors} location mismatch(es).")
        print("Run with --fix to auto-move files.")
    else:
        print("All file locations match issue labels.")

    if warnings:
        print(f"{warnings} status warning(s). Review manually.")

    if do_fix:
        os.system(f"cd {ROOT} && git add backlogs/ 2>/dev/null || true")
        print(f"{fixes} fix(es) applied.")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
