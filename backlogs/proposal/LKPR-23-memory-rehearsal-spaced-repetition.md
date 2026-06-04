---
id: LKPR-23
title: Memory Rehearsal (Spaced Repetition for Agent Memory)
type: feature
status: S:proposal
priority: P3:low
sprint: unplanned
rice_score: ~
filed_by: Hermes
github_issue: 65
filed_date: 2026-05-23
---

# [LKPR-23] Memory Rehearsal (Spaced Repetition for Agent Memory)

## Problem

Memory decay (LKPR-9) handles forgetting, but there's no active retention mechanism. Important memories — project constraints, user preferences, critical facts — get buried simply because they aren't frequently queried. The agent never thinks about memory, but without active retention, disuse punishes everything equally — obsolete knowledge and vital facts alike.

## Solution

Track `last_accessed`, `access_frequency`, and `retention_priority` per memory. A lightweight cron (or inline check during `lore_search`) identifies memories overdue for review based on spaced repetition intervals (1d → 3d → 7d → 30d). Overdue memories get:

- A temporary score boost during search (passive rehearsal), OR
- Proactive push via `lore_surface` (active rehearsal, if LKPR-11 is built)

Think: Anki for agent memory. Periodic nudges with summary cards: "You haven't used this critical fact in 5 days — here's a refresher."

**Estimated effort: M (~2-3 days).** New `services/rehearsal.py` module, SQLite migration for retention fields, integration with search pipeline. Smaller scope than sleep cycle (LKPR-13) since it reuses existing infrastructure.

## Acceptance Criteria

- [ ] Memories have `last_accessed`, `access_frequency`, `retention_priority` fields in SQLite
- [ ] Spaced repetition intervals (1d → 3d → 7d → 30d) determined by priority tier
- [ ] Overdue memories get a temporary score boost during `lore_search`
- [ ] Integration: memories are automatically bumped on every `lore_search` hit
- [ ] No user-visible configuration surface (keep it automatic)

## Affected Files

**Backend:**

- `src/lorekeeper/services/rehearsal.py` — new: spaced repetition logic
- `src/lorekeeper/services/search.py` — boost overdue memories
- `src/lorekeeper/` — SQLite migration for retention tracking fields
- `scripts/` — optional: cron entry if proactive push is added

**Dashboard (if applicable):**

- `_none_` — invisible to users, purely backend

## Dependencies

- LKPR-11 (lore_surface): if active rehearsal path is taken, needs the proactive push tool
- LKPR-9 (decay): rehearsal is complementary — decay punishes neglect, rehearsal rewards importance. Can be built independently.

## Open Questions

- Should rehearsal be inline (every search) or cron-based? Inline is simpler but adds per-search overhead.
- How to distinguish "seldom queried but critical" from "seldom queried and irrelevant"? Users marking confidence/importance is the clearest signal — but that's not currently scoped.

## Notes

Proposal from daily brainstorm cron (2026-05-23). Not urgent. Closes the gap between "old stuff decays" and "old stuff might be the most important thing you know."

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
