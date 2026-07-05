#!/usr/bin/env bash
# Check PR/branch size against insertion and file-count thresholds.
#
# Usage (git hook):
#   scripts/check_pr_size.sh [base-ref]          # base-ref defaults to origin/main
#
# Usage (CI — base ref passed from workflow):
#   scripts/check_pr_size.sh origin/main
#
# Exit codes: 0 = pass, 1 = hard failure (exceeds both thresholds)
# GitHub Actions annotations (::error:: / ::warning::) are emitted when
# GITHUB_ACTIONS=true so they render in the workflow summary.

set -euo pipefail

BASE="${1:-origin/main}"

# Thresholds — set via environment variables (all required).
MAX_INSERTIONS="${PR_MAX_INSERTIONS}"
MAX_FILES="${PR_MAX_FILES}"
WARN_INSERTIONS="${PR_WARN_INSERTIONS}"
WARN_FILES="${PR_WARN_FILES}"

# Colon-separated list of path prefixes excluded from the size gate.
# Set PR_EXCLUDE_PREFIXES="docs/:backlogs/:generated/" — empty means nothing excluded.
IFS=':' read -ra EXCLUDE_PREFIXES <<< "${PR_EXCLUDE_PREFIXES:-}"

# ── helpers ──────────────────────────────────────────────────────────────────

is_excluded() {
  local filename="$1"
  for prefix in "${EXCLUDE_PREFIXES[@]}"; do
    [[ "$filename" == "$prefix"* ]] && return 0
  done
  return 1
}

emit_error() {
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "::error::$*"
  else
    echo "ERROR: $*" >&2
  fi
}

emit_warning() {
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "::warning::$*"
  else
    echo "WARNING: $*" >&2
  fi
}

# ── diff ─────────────────────────────────────────────────────────────────────

# Ensure base ref is available (no-op if already fetched or local)
git fetch origin "${BASE#origin/}" --quiet 2>/dev/null || true

filtered_additions=0
filtered_files=0

while IFS=$'\t' read -r additions _deletions filename; do
  # Binary files show "-" for counts — skip them
  [[ "$additions" == "-" ]] && continue
  is_excluded "$filename" && continue
  filtered_additions=$(( filtered_additions + additions ))
  filtered_files=$(( filtered_files + 1 ))
done < <(git diff --numstat "${BASE}...HEAD")

excluded_label="${EXCLUDE_PREFIXES[*]}"

echo ""
echo "  Files changed : ${filtered_files} / ${MAX_FILES}  (warn at ${WARN_FILES})"
echo "  Lines added   : ${filtered_additions} / ${MAX_INSERTIONS}  (warn at ${WARN_INSERTIONS})"
echo "  Excluded      : ${excluded_label}"
echo ""

# ── thresholds ────────────────────────────────────────────────────────────────

if (( filtered_additions > MAX_INSERTIONS && filtered_files > MAX_FILES )); then
  emit_error "${filtered_additions} insertions across ${filtered_files} files exceeds" \
    "${MAX_INSERTIONS}/${MAX_FILES} threshold." \
    "Large PRs skip depth review. Split into smaller PRs per concern."
  exit 1
fi

if (( filtered_additions > WARN_INSERTIONS || filtered_files > WARN_FILES )); then
  emit_warning "${filtered_additions} insertions across ${filtered_files} files —" \
    "large PR. Consider splitting into smaller changes."
fi

exit 0
