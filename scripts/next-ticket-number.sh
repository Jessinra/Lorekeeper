#!/usr/bin/env bash
# next-ticket-number.sh — Get the next available LKPR ticket number
# Reads from GitHub Issues (authoritative) so it works even without latest git pull.
# Usage: ./scripts/next-ticket-number.sh
# Output: "LKPR-43" — just the number, no extra text (machine-parseable with -m flag)
#   With -m flag: human-friendly message with explanation
set -euo pipefail

MODE="${1:-}"

REPO="Jessinra/Lorekeeper"

# Fetch all open+closed issues, extract LKPR-N numbers, find max
NEXT=$(gh issue list --state all --json title --limit 200 --repo "$REPO" 2>/dev/null \
  | python3 -c "
import json, sys, re
data = json.load(sys.stdin)
nums = []
for issue in data:
    m = re.search(r'LKPR-(\d+)', issue['title'])
    if m:
        nums.append(int(m.group(1)))
if nums:
    print(max(nums) + 1)
else:
    print(1)
")

if [ "$MODE" = "-m" ]; then
  echo "Next ticket number: LKPR-${NEXT}  (from GitHub Issues — sequential, never fill gaps)"
else
  echo "LKPR-${NEXT}"
fi