---
id: LKPR-41
title: Memory Changelog / Version History (lore_diff / lore_history / lore_rollback)
type: feature
status: S:proposal
priority: P2:medium
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 76
filed_date: 2026-05-27
---

# [LKPR-41] Memory Changelog / Version History

## Problem

When `lore_update` fires (via user feedback or session-end), the old version of that memory is gone permanently. You can't see what changed, roll back a bad update, or audit how an agent's understanding evolved. As Lorekeeper accumulates weeks of memory, this creates a blind trust problem — you don't know where a fact came from or what it replaced.

## Solution

Versioned memories — every update snapshots the previous version. Three lightweight MCP tools:

- `lore_history(lore_id)` — returns timeline of versions with timestamps and trigger source (user feedback / agent update / auto-consolidation)
- `lore_diff(lore_id, v1, v2)` — structured diff between any two versions
- `lore_rollback(lore_id, version=N)` — reverts to earlier version (soft-delete newer ones)

A new `memory_versions` table (lore_id, version, content snapshot, diff, source, timestamp). Append-only — one extra write per update.

## Acceptance Criteria

- [ ] `lore_history` returns version timeline sorted by timestamp, with trigger source
- [ ] `lore_diff` returns structured diff between any two versions
- [ ] `lore_rollback` reverts to target version, soft-deletes newer ones
- [ ] Every `lore_update` auto-snapshots the previous state
- [ ] Dashboard has a version history view for any memory

## Affected Files

**Backend:**

- `src/lorekeeper/services/` — new `memory_version_store.py`
- `src/lorekeeper/handlers.py` — new handlers for `lore_history`, `lore_diff`, `lore_rollback`
- `src/lorekeeper/orchestrator.py` — hook into update path to snapshot

**Dashboard:**

- Memory detail page — version timeline tab, diff viewer

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] `lorekeeper-reconcile` — may need update to work with versioned memories
- **Backlog**: [ ] N/A

## Open Questions

- Should versioning be opt-in per memory type, or always-on?
- Retention policy — keep all versions forever, or cap at N?

## Notes

Originated from daily-ideas cron (2026-05-27). Idea 1, approved as P2.