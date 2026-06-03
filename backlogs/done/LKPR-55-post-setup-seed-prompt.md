---
id: LKPR-55
title: Post-setup seed prompt — agent auto-populates first memories
type: feature
status: S:done
priority: P2:medium
sprint: ~
rice_score: 45.0  # R:6 I:9 C:90% E:0.5d
filed_by: Jason
filed_date: 2026-06-03
resolved_date: 2026-06-03
---

# [LKPR-55] Post-setup seed prompt — agent auto-populates first memories

## Problem

After running `setup.sh`, Lorekeeper is configured with zero memories. The user sees an empty dashboard and has no idea what to do next. The "value" is invisible until the agent actually starts remembering things.

The first experience after setup should demonstrate value immediately — show the user that Lorekeeper works by having it already contain something meaningful.

## Solution

Add a post-setup block to `scripts/setup.sh` that prints a ready-to-paste prompt. The user copies it into any connected agent, and the agent auto-seeds its own identity.

**Why this works:**
- **Zero effort** — user just pastes one block of text
- **Zero assumptions** — works with any agent (Hermes, Claude Code, Cursor, Claude Desktop, etc.)
- **Immediate value** — after running it, the dashboard shows real memories about the agent itself
- **Proves the loop** — user sees "agent reads config → remembers → I can see it in the dashboard"
- **One line of bash** — literally just an `echo` block

## Acceptance Criteria

- [x] After MCP/prompt/skills injection completes, setup.sh prints the seed prompt block
- [x] Block is clearly formatted with a visual separator and a single copy-paste instruction
- [x] Block only shows when at least one agent was detected (not during dev-only re-runs)
- [x] Block uses the same prompt text for all agent types — intentionally generic
- [x] Works with Hermes, Claude Code, and Cursor (the three detected agent types)

## Required Updates

- **README.md**: [ ] Consider mentioning the seed prompt in the setup section
- **Skills**: [ ] None needed — this is pure bash, no skill changes

## Affected Files

- `scripts/setup.sh` — add seed prompt block after the summary table, before "Setup complete"

## Dependencies

_None_ — self-contained.

## Notes

The prompt is intentionally generic — no agent-specific instructions. Any agent that can call `lore_search`/`lore_remember`/`lore_insert` can execute it.