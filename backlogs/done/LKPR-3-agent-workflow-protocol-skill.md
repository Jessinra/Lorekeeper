---
id: LKPR-3
title: Ship lorekeeper-protocol skill file for plug & play agent onboarding
type: feature
status: done
priority: critical
sprint: 1
rice_score: 45.0  # R:9 I:9 C:80% E:1w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-3] Ship lorekeeper-protocol skill file for plug & play agent onboarding

## Problem
Any agent can install lorekeeper but won't know when to call what. Without guidance, agents either over-call (expensive) or under-call (memory stays stale). The platform is only as good as how it's used.

## Solution
Ship an opinionated **lorekeeper-protocol skill file** encoding the full usage protocol:
- Session start → `lore_search` (load context + feedback on results)
- Mid-session topic shift → `lore_search` again
- Every ~10 inserts → manual spot-check for near-duplicates via `lore_search` + `lore_update`
- After 5+ sessions on same topic → `lore_processed_sessions` + `lore_search` → agent synthesizes consolidated summary via `lore_insert`
- Session end → `lore_insert` (new learnings) + `lore_reflect`

The skill IS the intelligence layer. Agent loads it once, follows it forever. Zero platform LLM cost.

## Acceptance Criteria
- [ ] `skills/lorekeeper-protocol.md` exists in the repo and is self-contained
- [ ] Any agent (Hermes, Claude Code, Cursor) can follow the skill with zero additional config
- [ ] `README.md` highlights the skill as the primary onboarding path
- [ ] Protocol covers: session start, mid-session, session end, and health-triggered actions

## Affected Files
- New: `skills/lorekeeper-protocol.md`
- `README.md` — highlight skill as primary onboarding path

## Dependencies
- LKPR-2 (`lore_health`) should exist before the health-triggered steps are useful, but skill can ship first with a TODO note

## Open Questions
_None_

## Notes
Highest leverage item for adoption — platform tools are useless without this. This is the "plug & play" north star in one file.
