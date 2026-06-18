---
id: LKPR-95
title: Agent Tags on Memories — optional tags dict + tags_filter on search
type: feature
status: S:proposal
priority: P3:low
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-15
github_issue: 217
---

# [LKPR-95] Agent Tags on Memories — optional tags dict + tags_filter on search

## Problem

Memories carry no cross-cutting metadata. In multi-agent environments where tags could be useful for sub-categorization within a namespace (e.g. `project: lorekeeper`, `topic: pricing`), there's no way to attach key-value metadata and filter on it.

Note: The original multi-agent scoping problem is now solved by namespace/env isolation (LKPR-38). Tags would be additive metadata, not a scoping mechanism.

## Solution

Add optional `tags` key-value dict to `lore_insert` and `lore_remember`, stored in SQLite metadata. Add `tags_filter` param to `lore_search` with AND semantics (all specified tags must match).

## Acceptance Criteria

- [ ] `lore_insert` accepts optional `tags` dict (key-value pairs)
- [ ] `lore_remember` accepts optional `tags` dict (key-value pairs)
- [ ] `tags` stored in SQLite metadata table
- [ ] `lore_search` supports `tags_filter` param (dict; returns memories matching ALL specified tags)
- [ ] Tags returned in search results alongside existing metadata
- [ ] No schema changes if `tags` not provided (backward compatible)

## Affected Files

- `src/lorekeeper/models.py` — add `tags` field
- `src/lorekeeper/services/memory_engine.py` — persist at insert time
- `src/lorekeeper/services/search.py` — return + filter on tags
- `src/lorekeeper/handlers.py` — expose in tool inputs/outputs

## Dependencies

None — independent of LKPR-18. Can be implemented in any order.

## Notes

Split from LKPR-18 Phase B (2026-06-15). Kept as independent P3 proposal.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
