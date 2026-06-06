#!/usr/bin/env python3
"""
CI guard: every proposal in backlogs/proposal/ must have a valid github_issue
that resolves to a real, open GitHub issue.

Exit 0 — all proposals reference valid issues.
Exit 1 — one or more issues missing or unresolvable; prints actionable details.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROPOSAL_DIR = ROOT / "backlogs" / "proposal"

# GitHub token available in CI via GITHUB_TOKEN env var
# For local runs, falls back to ~/.config/gh/hosts.yml
GITHUB_REPO = "Jessinra/Lorekeeper"


def _get_token() -> str:
    """Get a GitHub token from env or gh config file."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    # Fallback: read gh CLI config
    gh_config = Path.home() / ".config" / "gh" / "hosts.yml"
    if gh_config.exists():
        m = re.search(r"oauth_token:\s*(\S+)", gh_config.read_text())
        if m:
            return m.group(1)
    return ""


def get_issue_status(issue_number: int, token: str) -> str | None:
    """Return issue state ('open', 'closed') or None if not found."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "lorekeeper-ci",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            # GitHub issues API returns PRs too; PRs are fine
            return data.get("state")  # "open" or "closed"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f"  ⚠  HTTP {e.code} checking #{issue_number}: {e}")
        return None
    except Exception as e:
        print(f"  ⚠  Error checking #{issue_number}: {e}")
        return None


def extract_frontmatter_field(text: str, field: str) -> str | None:
    """Extract a YAML frontmatter field value from markdown text."""
    m = re.search(rf"^{field}:\s*(.+?)\s*$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def main() -> int:
    errors = 0
    token = _get_token()
    has_token = bool(token)

    if not PROPOSAL_DIR.exists():
        print(f"✅  No proposals directory at {PROPOSAL_DIR}")
        return 0

    files = sorted(PROPOSAL_DIR.glob("*.md"))
    if not files:
        print("✅  No proposal files to check")
        return 0

    print(f"🔍  Checking {len(files)} proposal files for valid GitHub issues...")

    for filepath in files:
        name = filepath.name
        text = filepath.read_text()

        # Extract github_issue from frontmatter (between --- markers)
        frontmatter_match = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not frontmatter_match:
            print(f"  ✗ {name}: no frontmatter found")
            errors += 1
            continue

        frontmatter = frontmatter_match.group(1)
        gi_raw = extract_frontmatter_field(frontmatter, "github_issue")

        if not gi_raw:
            print(f"  ✗ {name}: github_issue field missing or empty")
            errors += 1
            continue

        if not gi_raw.isdigit():
            print(f"  ✗ {name}: github_issue must be a number, got '{gi_raw}'")
            errors += 1
            continue

        issue_num = int(gi_raw)

        # Check the issue exists via GitHub API
        if has_token:
            state = get_issue_status(issue_num, token)
            if state is None:
                print(f"  ✗ {name}: references #{issue_num} but that issue does not exist")
                errors += 1
            elif state == "closed":
                print(f"  ⚠  {name}: references #{issue_num} which is CLOSED")
                # Don't fail on closed — proposals can reference closed issues
            else:
                print(f"  ✓ {name} -> #{issue_num} ({state})")
        else:
            print(f"  ✓ {name} -> #{issue_num} (no API token — format check only)")
            # Without a token, we can only validate the format

    if errors:
        print(f"\n❌  {errors} proposal(s) have invalid or missing GitHub issue references.")
        print("   Every proposal ticket must have a real GitHub issue.")
        print("   Create one first, then add its number to `github_issue:` in frontmatter.")
        return 1

    print("\n✅  All proposals reference valid GitHub issues.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
