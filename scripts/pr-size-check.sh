#!/usr/bin/env bash
# pr-size-check.sh — enforce PR size discipline
#
# Works in both GitHub Actions and local dev.
# Exits 0 (pass/warn), 1 (hard fail XL), or 2 (usage error).
#
# Size tiers (multi-dimensional — worst dimension wins):
#
#   S   ≤10 files AND ≤500 total AND ≤350 add|del   → ✅ Green  — ideal
#   M   >10 files OR  >500 total OR  >350 add|del   → 🟡 Yellow — acceptable
#   L   >20 files OR  >1000 total OR >750 add|del   → 🟠 Orange — reconsider splitting
#   XL  >50 files OR  >2000 total OR >1500 add|del  → ❌ Red    — hard fail (add [large-pr] to bypass)
#
# Override flag: add [large-pr] to PR title or commit message to bypass XL hard fail.
#
# Usage:
#   bash scripts/pr-size-check.sh                  # auto-detect CI env
#   bash scripts/pr-size-check.sh --base main      # explicit base branch
#   bash scripts/pr-size-check.sh --dry-run        # print stats, always exit 0

set -euo pipefail

# ── Thresholds ──────────────────────────────────────────────────────────────
# S/M boundary
S_TOTAL=500;  S_ADD_DEL=350;  S_FILES=10
# M/L boundary
L_TOTAL=1000; L_ADD_DEL=750;  L_FILES=20
# L/XL boundary (hard fail)
XL_TOTAL=2000; XL_ADD_DEL=1500; XL_FILES=50
# ────────────────────────────────────────────────────────────────────────────

BASE_BRANCH="${BASE_BRANCH:-main}"
DRY_RUN=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --base)    BASE_BRANCH="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        *)         echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

# Detect [large-pr] override in PR title (GitHub Actions) or last commit
OVERRIDE=false
if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then
    PR_TITLE="${GITHUB_PR_TITLE:-}"
    if [[ "$PR_TITLE" == *"[large-pr]"* ]]; then
        OVERRIDE=true
    fi
fi
LAST_COMMIT_MSG=$(git log -1 --pretty=%s 2>/dev/null || echo "")
if [[ "$LAST_COMMIT_MSG" == *"[large-pr]"* ]]; then
    OVERRIDE=true
fi

# Count lines changed — exclude generated/non-meaningful files
EXCLUDE_PATTERNS=(
    ':!uv.lock'
    ':!*.lock'
    ':!*.json'
    ':!assets/*.png'
    ':!assets/*.jpg'
    ':!assets/*.webp'
    ':!docs/plans/*'
)

DIFF_OUTPUT=$(git diff --shortstat "${BASE_BRANCH}...HEAD" -- "${EXCLUDE_PATTERNS[@]}" 2>/dev/null || \
              git diff --shortstat "origin/${BASE_BRANCH}...HEAD" -- "${EXCLUDE_PATTERNS[@]}" 2>/dev/null || \
              echo "")

if [[ -z "$DIFF_OUTPUT" ]]; then
    echo "ℹ️  No diff found against ${BASE_BRANCH} — nothing to check"
    exit 0
fi

# Parse: "X files changed, Y insertions(+), Z deletions(-)"
FILES=$(echo "$DIFF_OUTPUT"    | grep -oE '[0-9]+ file'      | grep -oE '[0-9]+' || echo "0")
ADDITIONS=$(echo "$DIFF_OUTPUT" | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || echo "0")
DELETIONS=$(echo "$DIFF_OUTPUT" | grep -oE '[0-9]+ deletion'  | grep -oE '[0-9]+' || echo "0")
TOTAL=$(( ${ADDITIONS:-0} + ${DELETIONS:-0} ))

# Worst single dimension (for tier classification)
WORST_DIM="lines (${TOTAL} total)"
WORST_TIER="S"

classify_tier() {
    local files=$1 total=$2 additions=$3 deletions=$4
    local tier="S"
    local reason=""

    if [[ $files -gt $XL_FILES || $total -gt $XL_TOTAL || $additions -gt $XL_ADD_DEL || $deletions -gt $XL_ADD_DEL ]]; then
        tier="XL"
        if   [[ $files     -gt $XL_FILES    ]]; then reason="${files} files (limit ${XL_FILES})"
        elif [[ $total     -gt $XL_TOTAL    ]]; then reason="${total} total lines (limit ${XL_TOTAL})"
        elif [[ $additions -gt $XL_ADD_DEL  ]]; then reason="${additions} additions (limit ${XL_ADD_DEL})"
        else                                         reason="${deletions} deletions (limit ${XL_ADD_DEL})"
        fi
    elif [[ $files -gt $L_FILES || $total -gt $L_TOTAL || $additions -gt $L_ADD_DEL || $deletions -gt $L_ADD_DEL ]]; then
        tier="L"
        if   [[ $files     -gt $L_FILES   ]]; then reason="${files} files (>${L_FILES})"
        elif [[ $total     -gt $L_TOTAL   ]]; then reason="${total} total lines (>${L_TOTAL})"
        elif [[ $additions -gt $L_ADD_DEL ]]; then reason="${additions} additions (>${L_ADD_DEL})"
        else                                        reason="${deletions} deletions (>${L_ADD_DEL})"
        fi
    elif [[ $files -gt $S_FILES || $total -gt $S_TOTAL || $additions -gt $S_ADD_DEL || $deletions -gt $S_ADD_DEL ]]; then
        tier="M"
        if   [[ $files     -gt $S_FILES   ]]; then reason="${files} files (>${S_FILES})"
        elif [[ $total     -gt $S_TOTAL   ]]; then reason="${total} total lines (>${S_TOTAL})"
        elif [[ $additions -gt $S_ADD_DEL ]]; then reason="${additions} additions (>${S_ADD_DEL})"
        else                                        reason="${deletions} deletions (>${S_ADD_DEL})"
        fi
    else
        reason="all dimensions within S limits"
    fi

    echo "${tier}|${reason}"
}

RESULT=$(classify_tier "${FILES:-0}" "$TOTAL" "${ADDITIONS:-0}" "${DELETIONS:-0}")
TIER="${RESULT%%|*}"
REASON="${RESULT##*|}"

echo ""
echo "📐 PR size summary"
echo "   Files   : ${FILES:-0}  (S≤${S_FILES}  M≤${L_FILES}  L≤${XL_FILES})"
echo "   Total   : ${TOTAL}  (S≤${S_TOTAL}  M≤${L_TOTAL}  L≤${XL_TOTAL})"
echo "   Adds    : ${ADDITIONS:-0}  (S≤${S_ADD_DEL}  M≤${L_ADD_DEL}  L≤${XL_ADD_DEL})"
echo "   Dels    : ${DELETIONS:-0}  (S≤${S_ADD_DEL}  M≤${L_ADD_DEL}  L≤${XL_ADD_DEL})"
echo "   Base    : ${BASE_BRANCH}"
echo "   Tier    : ${TIER}  ← ${REASON}"

if $DRY_RUN; then
    echo ""
    echo "ℹ️  Dry-run mode — no enforcement"
    exit 0
fi

if $OVERRIDE; then
    echo ""
    echo "⚠️  [large-pr] override — bypassing XL hard fail"
    echo "    Large PRs get fewer meaningful review comments. Split when possible."
    exit 0
fi

case "$TIER" in
    S)
        echo ""
        echo "✅  Tier S — ideal PR size. Reviews are fast and thorough."
        exit 0
        ;;
    M)
        echo ""
        echo "🟡  Tier M — acceptable. Consider splitting if this covers multiple concerns."
        exit 0
        ;;
    L)
        echo ""
        echo "🟠  Tier L — large PR (${REASON})."
        echo "    Review quality drops at this size. Strongly recommend splitting."
        echo "    CI still passes — this is a warning."
        exit 0
        ;;
    XL)
        echo ""
        echo "❌  Tier XL — hard fail (${REASON})"
        echo ""
        echo "    PRs at XL size average ~1.8 meaningful review comments."
        echo "    PRs at S size get ~6x more thorough reviews."
        echo ""
        echo "    How to fix:"
        echo "    1. Split this PR into smaller, focused changes"
        echo "    2. If truly unsplittable, add [large-pr] to your PR title or commit message"
        echo "       and explain why in the PR description"
        echo ""
        echo "    Example: git commit --amend -m \"[large-pr] chore: initial scaffold\""
        echo ""
        exit 1
        ;;
esac
