#!/usr/bin/env bash
# validate-ticket.sh — check backlog ticket format
# Called by pre-commit hook for any staged LKPR-*.md file.
# Blocks commit on format violations.
#
# Usage: scripts/validate-ticket.sh [file...]
#   If no files given, checks all staged LKPR-*.md files in backlogs/
#   If files given, checks only those.

set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
cd "$REPO_ROOT"

VALID_TYPES="feature|bug|enhancement|research|chore"
VALID_STATUSES="S:proposal|S:ready|S:in-progress|S:review|S:done|S:deferred|S:cancelled"
VALID_PRIORITIES="P0:critical|P1:high|P2:medium|P3:low"

# Required frontmatter fields
REQUIRED_FIELDS="id|title|type|sprint|rice_score|filed_by|filed_date"

# Required sections (in order) — use array to handle spaces
REQUIRED_SECTIONS=("Problem" "Solution" "Acceptance Criteria" "Required Updates")

errors=0

# Helper: extract body content between a section heading and the next heading (or EOF)
# Usage: section_body "body_text" "Section Name"
# Strips the opening ## line; stops at next ## without including it.
section_body() {
  local body="$1" section="$2"
  echo "$body" | awk -v section="^## $section\$" '
    $0 ~ section { found=1; next }
    found && /^## / { exit }
    found { print }
  '
}

# Helper: extract a frontmatter field value, stripping inline comments
# sed 's/[[:space:]]*#.*//' removes comments like "feature # comment" → "feature"
get_field() {
  local frontmatter="$1" field="$2"
  echo "$frontmatter" | grep "^$field:" | sed 's/^[^:]*:[[:space:]]*//; s/[[:space:]]*#.*//'
}

# Collect files to validate
files=("$@")
if [ ${#files[@]} -eq 0 ]; then
  # Get staged backlog files
  while IFS= read -r file; do
    files+=("$file")
  done < <(git diff --cached --name-only --diff-filter=ACM | grep -E 'backlogs/.*LKPR-[0-9]+.*\.md$' || true)
fi

if [ ${#files[@]} -eq 0 ]; then
  exit 0  # no backlog files changed
fi

for file in "${files[@]}"; do
  # Skip TEMPLATE.md — not a real ticket
  basename "$file" | grep -q '^TEMPLATE\.md$' && continue

  [ ! -f "$file" ] && continue

  errors_file=0

  # Read frontmatter between --- markers
  frontmatter=$(sed -n '/^---$/,/^---$/p' "$file" | sed '1d;$d' 2>/dev/null)

  # Check required fields
  for field in $(echo "$REQUIRED_FIELDS" | tr '|' ' '); do
    if ! echo "$frontmatter" | grep -q "^$field:"; then
      echo "  ✗ $file: missing frontmatter field '$field'"
      errors_file=$((errors_file + 1))
    fi
  done

  # Validate type value (strip inline comments)
  type_val=$(get_field "$frontmatter" "type")
  if [ -n "$type_val" ] && ! echo "$VALID_TYPES" | tr '|' '\n' | grep -qx "$type_val"; then
    echo "  ✗ $file: invalid type '$type_val' (valid: $VALID_TYPES)"
    errors_file=$((errors_file + 1))
  fi

  # Check required sections (after frontmatter)
  body=$(sed '1,/^---$/d' "$file")
  for section in "${REQUIRED_SECTIONS[@]}"; do
    if ! echo "$body" | grep -q "^## $section"; then
      echo "  ✗ $file: missing required section '## $section'"
      errors_file=$((errors_file + 1))
    fi
  done

  # Validate Acceptance Criteria format (each AC must start with - [ ] or - [x])
  ac_block=$(section_body "$body" "Acceptance Criteria")
  if [ -n "$ac_block" ]; then
    while IFS= read -r line; do
      stripped=$(echo "$line" | sed 's/^[[:space:]]*//')
      [ -z "$stripped" ] && continue
      if ! echo "$stripped" | grep -qE '^- \[[ x]\] '; then
        echo "  ✗ $file: AC line must start with '- [ ]' or '- [x]': $stripped"
        errors_file=$((errors_file + 1))
      fi
    done <<< "$ac_block"
  fi

  # Validate Required Updates checkboxes
  ru_block=$(section_body "$body" "Required Updates")
  if [ -n "$ru_block" ]; then
    while IFS= read -r line; do
      stripped=$(echo "$line" | sed 's/^[[:space:]]*//')
      [ -z "$stripped" ] && continue
      # Lines with checkbox patterns: **Label**: [ ] text or **Label**: [x] text
      if echo "$stripped" | grep -qE '^\*\*[^*]+\*\*:'; then
        if ! echo "$stripped" | grep -qE '\[ \]|\[x\]|N/A'; then
          echo "  ✗ $file: Required Updates item must have [ ], [x], or N/A: $stripped"
          errors_file=$((errors_file + 1))
        fi
      fi
    done <<< "$ru_block"
  fi

  if [ "$errors_file" -gt 0 ]; then
    errors=$((errors + errors_file))
  fi
done

if [ "$errors" -gt 0 ]; then
  echo ""
  echo "❌  Ticket format validation failed — $errors error(s). Fix and retry."
  exit 1
fi

exit 0