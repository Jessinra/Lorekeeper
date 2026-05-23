---
id: LKPR-22
title: Time-Travel Queries (lore_search_at for Memory Audit Trail)
type: feature
status: proposal
priority: low
sprint: unplanned
rice_score: ~
filed_by: Hermes
filed_date: 2026-05-23
---

# [LKPR-22] Time-Travel Queries (lore_search_at for Memory Audit Trail)

## Problem
Memory is updated in place. When an agent corrects a wrong fact or a user explicitly updates a memory, the old version is gone. This makes agent self-debugging impossible — "Why did I recommend X yesterday? What did my memory say at the time?" There is no audit trail.

## Solution
Every `lore_insert` and `lore_update` writes to a WAL (write-ahead log) in SQLite — a full snapshot of the lore entry with timestamp + delta. Then:

- `lore_search_at(query, timestamp)` — returns what the memory state was at time T. Reconstructs by replaying the WAL up to that point for modified entries, using the live store for everything else.
- `lore_diff(lore_id, t1, t2)` — shows what changed between two points in time (phased, lower priority).

The WAL is append-only and bounded (auto-prune after N days or configurable retention). Storage cost is approximately one extra row per write — negligible.

**Estimated effort: L overall (phased).**
- Phase 1 — WAL recording only (M, ~2 days, pure infrastructure)
- Phase 2 — `lore_search_at` reconstruction logic (M, ~2-3 days)
- Phase 3 — `lore_diff` (S, ~1 day)

The search_at reconstruction is the tricky part: WAL-replay only the modified entries, return the rest from the live store.

## Acceptance Criteria
- [ ] Phase 1: every `lore_insert` and `lore_update` writes a snapshot+delta to a WAL table
- [ ] Phase 1: WAL auto-prunes after configurable retention (default N days)
- [ ] Phase 2: `lore_search_at(query, timestamp)` returns correct state at T
- [ ] Phase 2: unmodified memories return current state (no replay overhead)
- [ ] Phase 3: `lore_diff(lore_id, t1, t2)` shows changes between two timestamps
- [ ] All MCP tool signatures match existing schemas pattern

## Affected Files

**Backend:**
- `src/lorekeeper/` — SQLite migration for WAL table
- `src/lorekeeper/services/memory_engine.py` — WAL recording on every write
- `src/lorekeeper/services/search.py` — `lore_search_at` reconstruction logic
- `src/lorekeeper/handlers.py` — new handlers for `lore_search_at` and `lore_diff`
- `src/lorekeeper/server.py` — register new MCP tools

**Dashboard (if applicable):**
- `_none_` for Phase 1-2. Phase 3 could add a history viewer.

## Dependencies
- _None_ — standalone feature, builds on existing storage infrastructure

## Open Questions
- What's the default retention period? 30 days? 90? Configurable? Needs a sensible default.
- For `lore_diff`: what format for the delta? Simple text diff, or structured field-level change tracking?
- Does the WAL need to be queryable directly, or only through `lore_search_at`?

## Notes
Proposal from daily brainstorm cron (2026-05-23). Not urgent, effort seems significant (phased approach recommended). Enables agent self-audit: check what the agent actually knew at decision time when debugging bad decisions. Also enables undoing bad updates and A/B testing memory strategies.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention