---
id: LKPR-28
github_issue: 25
title: Add inline links param to lore_insert for one-call insert + link
type: feature
sprint: ~
rice_score: ~
filed_by: Akane (PM)
filed_date: 2026-05-23
---

# [LKPR-28] Add inline links param to lore_insert for one-call insert + link

## Problem

Creating a linked memory currently requires two calls: `lore_insert` first (returns `memory_id`), then a second call to link it. There's no MCP tool to create links at all yet — the agent would need to call `link_store` directly. This friction means most memories never get linked, even when the agent clearly knows the relationship (it has the source `memory_id` from the preceding `lore_search`).

## Solution

Add an optional `links` parameter to `lore_insert` that accepts a list of link descriptors. Each descriptor specifies a target `memory_id`, `relation_type`, and optional `reason`.

**Agent flow becomes:**

```
# Before: two calls, no link tool
id = lore_insert(title="Token refresh", content="...")
#   ... no way to link it without a second tool

# After: one call
lore_insert(
  title="Token refresh",
  content="Access tokens expire after 1h",
  links=[{
    "memory_id": "abc-123",
    "relation": "used_in",
    "reason": "part of OAuth flow"
  }]
)
```

The agent already has the target `memory_id` from the preceding `lore_search` query — it just needs to pass it through. Zero extra round trips.

## Acceptance Criteria

- [ ] `lore_insert` accepts optional `links: [{memory_id, relation, reason?}]` on each memory item (not at top level — link per inserted memory)
- [ ] Each link is validated (target must exist, relation_type must be valid)
- [ ] Invalid target or relation type returns a clear error, does NOT silently drop the link
- [ ] The inserted memory itself is still created even if a link fails (partial failure)
- [ ] MCP tool docstring updated to show the new param
- [ ] Unit test: insert with links creates both memory and link records
- [ ] Unit test: invalid target returns error in errors[] but memory is still inserted

## Affected Files

**Backend:**

- `src/lorekeeper/schemas.py` — update `LoreInsertInput` model
- `src/lorekeeper/services/orchestrator.py` — handle links during insert
- `src/lorekeeper/server.py` — update docstring/tool description
- `tests/test_lore_related.py` or `tests/test_orchestrator.py` — link-on-insert tests

**Dashboard:**
_none_ — existing memory detail view already shows links

## Dependencies

_None_ — `link_store.link_memories()` already exists. No schema changes needed.

## Required Updates

- **CLAUDE.md**: [ ] N/A — no behavior change, only fewer calls
- **README.md**: [ ] Document the `links` parameter in `lore_insert` API docs
- **Skills**: [ ] Update `memory-linker` and `memory-reorganizer` skills to use inline links instead of two-step insert+link
- **Backlog**: [ ] N/A — LKPR-27 already noted as complementary

## Open Questions

- Should links be per-memory-item or at the top level for batch inserts? Per-item is more flexible — a single `lore_insert` can create multiple memories each linked to different targets.
- Should it also support creating links BETWEEN items in the same insert batch? (Insert A links to Insert B — but B doesn't have its ID yet. This would need two-phase insert.)

## Notes

This is the **intentional link** counterpart to LKPR-27 (auto-link via vector similarity). They solve different problems:

- **LKPR-27** = machine-detected clusters (passive, automatic)
- **LKPR-28** = agent-intended relations (active, explicit) — **higher value per link**
