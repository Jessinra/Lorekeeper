#!/usr/bin/env bash
# pr-size-check.sh — enforce PR size discipline
#
# Works in both GitHub Actions and local dev.
# Exits 0 (pass), 1 (hard fail >600 lines), or 2 (usage error).
#
# Soft limits  : warn at 200, amber at 400 (posts PR comment in CI)
# Hard limit   : fail at 600 (blocks CI)
# Override flag: add [large-pr] to PR title or commit message to bypass hard limit
#
# Usage:
#   bash scripts/pr-size-check.sh                  # auto-detect CI env
#   bash scripts/pr-size-check.sh --base main      # explicit base branch
#   bash scripts/pr-size-check.sh --dry-run        # print stats, always exit 0
#
# Install: the script is called by .github/workflows/ci.yml on every PR.
# Local:   bash scripts/pr-size-check.sh --base main

set -euo pipefail

WARN_LINES=200
AMBER_LINES=400
HARD_LINES=600

BASE_BRANCH="${BASE_BRANCH:-main}"
DRY_RUN=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --base)   BASE_BRANCH="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        *)         echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

# Detect override flag in PR title (GitHub Actions) or commit message
OVERRIDE=false
if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then
    PR_TITLE="${GITHUB_PR_TITLE:-}"
    if [[ "$PR_TITLE" == *"[large-pr]"* ]]; then
        OVERRIDE=true
    fi
fi
# Also check last commit message
LAST_COMMIT_MSG=$(git log -1 --pretty=%s 2>/dev/null || echo "")
if [[ "$LAST_COMMIT_MSG" == *"[large-pr]"* ]]; then
    OVERRIDE=true
fi

# Count lines changed (additions + deletions) excluding generated/non-meaningful files
EXCLUDE_PATTERNS=(
    ':!uv.lock'
    ':!*.lock'
    ':!*.json'     # package-lock.json, etc.
    ':!assets/*.png'
    ':!assets/*.jpg'
    ':!assets/*.webp'
    ':!docs/plans/*'  # generated plans are often large
)

# Get the diff stat
DIFF_OUTPUT=$(git diff --shortstat "${BASE_BRANCH}...HEAD" -- "${EXCLUDE_PATTERNS[@]}" 2>/dev/null || \
              git diff --shortstat "origin/${BASE_BRANCH}...HEAD" -- "${EXCLUDE_PATTERNS[@]}" 2>/dev/null || \
              echo "")

if [[ -z "$DIFF_OUTPUT" ]]; then
    echo "ℹ️  No diff found against ${BASE_BRANCH} — nothing to check"
    exit 0
fi

# Parse additions and deletions from: "X files changed, Y insertions(+), Z deletions(-)"
ADDITIONS=$(echo "$DIFF_OUTPUT" | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || echo "0")
DELETIONS=$(echo "$DIFF_OUTPUT" | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+' || echo "0")
TOTAL=$((${ADDITIONS:-0} + ${DELETIONS:-0}))

# File count
FILES=$(echo "$DIFF_OUTPUT" | grep -oE '[0-9]+ file' | grep -oE '[0-9]+' || echo "0")

echo ""
echo "PR size: ${TOTAL} lines changed (${ADDITIONS:-0} added, ${DELETIONS:-0} deleted) across ${FILES:-0} files"
echo "Base branch: ${BASE_BRANCH}"

if $DRY_RUN; then
    echo "ℹ️  Dry-run mode — no enforcement"
    exit 0
fi

if $OVERRIDE; then
    echo "⚠️  [large-pr] override detected — bypassing size limit"
    echo "    Remember: large PRs get fewer meaningful review comments. Split when possible."
    exit 0
fi

# Evaluate thresholds
if [[ $TOTAL -le $WARN_LINES ]]; then
    echo "✅  Green — ideal PR size (<${WARN_LINES} lines). Reviews are fast and thorough."
    exit 0

elif [[ $TOTAL -le $AMBER_LINES ]]; then
    echo "🟡  Yellow warning — ${TOTAL} lines (${WARN_LINES}–${AMBER_LINES} range)."
    echo "    Acceptable, but consider splitting if the PR covers multiple concerns."
    exit 0

elif [[ $TOTAL -le $HARD_LINES ]]; then
    echo "🟠  Orange warning — ${TOTAL} lines (${AMBER_LINES}–${HARD_LINES} range)."
    echo "    Review quality drops significantly above ${AMBER_LINES} lines."
    echo "    Strongly recommend splitting this PR."
    # Orange is a warning, not a failure — CI still passes
    exit 0

else
    echo ""
    echo "❌  HARD LIMIT EXCEEDED — ${TOTAL} lines changed (limit: ${HARD_LINES})"
    echo ""
    echo "    PRs above ${HARD_LINES} lines get ~1.8 meaningful review comments on average."
    echo "    PRs under 200 lines get ~6x more thorough reviews."
    echo ""
    echo "    How to fix:"
    echo "    1. Split this PR into smaller, focused changes"
    echo "    2. If this truly cannot be split, add [large-pr] to your PR title or commit message"
    echo "       and explain why in the PR description"
    echo ""
    echo "    Example: git commit --amend -m \"[large-pr] chore: initial scaffold\""
    echo ""
    exit 1
fi
