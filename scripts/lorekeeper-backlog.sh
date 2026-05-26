#!/bin/bash
# lorekeeper-backlog — list backlog tickets grouped by status
# Usage: ./lorekeeper-backlog.sh [status_filter]
#   e.g. ./lorekeeper-backlog.sh proposal    # only proposals
#        ./lorekeeper-backlog.sh              # all statuses
#
# Numbering convention: SEQUENTIAL (highest existing number + 1).
# Gaps are filled by done tickets moved to backlogs/done/.
# NEVER fill gaps — always use highest+1.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKLOG_DIR="${BACKLOG_DIR:-$SCRIPT_DIR/../backlogs}"

# All valid statuses, in display order
STATUSES=(proposal backlog in-progress review done deferred cancelled)

# If a filter arg is given, only show that status
if [ -n "$1" ]; then
    STATUSES=("$1")
fi

echo "╔══════════════════════════════════════╗"
echo "║       Lorekeeper Backlog             ║"
echo "╚══════════════════════════════════════╝"
echo ""

found_any=false
for status in "${STATUSES[@]}"; do
    files=()
    while IFS= read -r -d '' file; do
        files+=("$file")
done < <(find "$BACKLOG_DIR" -maxdepth 2 -name "*.md" ! -name "TEMPLATE.md" -exec grep -l "^status: $status" {} \; 2>/dev/null | sort | tr '\n' '\0')

    count=${#files[@]}
    if [ "$count" -gt 0 ]; then
        found_any=true
        echo "━━━ $status ($count) ━━━"
        for file in "${files[@]}"; do
            basename=$(basename "$file" .md)
            id=$(grep -m1 "^id:" "$file" | sed 's/^id: *//')
            title=$(grep -m1 "^title:" "$file" | sed 's/^title: *//')
            priority=$(grep -m1 "^priority:" "$file" | sed 's/^priority: *//')
            echo "  $id  $title  [$priority]"
        done
        echo ""
    fi
done

if ! $found_any; then
    echo "  No tickets found for status: $1"
    echo ""
fi

# Check for duplicate ticket numbers (in both backlogs/ and backlogs/done/)
echo "─── Integrity ───"
dupes=$(find "$BACKLOG_DIR" -maxdepth 2 -name "LKPR-*.md" -exec basename {} \; | grep -oE 'LKPR-[0-9]+' | sort | uniq -d)
if [ -n "$dupes" ]; then
    echo "  ⚠ DUPLICATE ticket numbers:"
    echo "$dupes" | while read -r num; do
        echo "     $num appears in:"
        find "$BACKLOG_DIR" -maxdepth 2 -name "$num*" -exec basename {} \;
    done
else
    echo "  ✓ No duplicate ticket numbers"
fi

# Latest ticket number — search BOTH backlogs/ and backlogs/done/ for sequential numbering
# Convention: highest existing number + 1. Gaps are from done tickets.
latest=$(find "$BACKLOG_DIR" -maxdepth 2 -name "LKPR-*.md" -exec basename {} \; | grep -oE 'LKPR-[0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1)
echo "  Next ticket number: LKPR-$((latest + 1))  (sequential — highest+1, never fill gaps)"