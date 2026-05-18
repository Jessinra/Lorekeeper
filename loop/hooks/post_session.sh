#!/usr/bin/env bash
# Post-session hook: appends a timestamped entry to loop/sessions/ for the reconcile agent.
# Wire this in ~/.claude/settings.json under hooks.postSession.
# Usage: called by Claude Code automatically after each session ends.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SESSIONS_DIR="$REPO_DIR/loop/sessions"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H%M)
SESSION_FILE="$SESSIONS_DIR/${DATE}-${TIME}.md"

mkdir -p "$SESSIONS_DIR"

cat > "$SESSION_FILE" <<'TEMPLATE'
---
date: REPLACE_DATE
topic: REPLACE_TOPIC
task_type: build|debug|review|design
---

## What was done

(brief summary)

## Decisions made

-

## Corrections received

(user pushback — strongest learning signal)

-

## Patterns observed

-

## Proposed updates

- [ ] CLAUDE.md:
- [ ] skill:
- [ ] memory:
TEMPLATE

# Replace placeholders
sed -i '' "s/REPLACE_DATE/$DATE/" "$SESSION_FILE"
sed -i '' "s/REPLACE_TIME/$TIME/" "$SESSION_FILE"

echo "Session log created: $SESSION_FILE"
