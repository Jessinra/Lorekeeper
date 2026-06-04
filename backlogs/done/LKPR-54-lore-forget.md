---
id: LKPR-54
title: lore_forget — explicit memory lifecycle control
type: enhancement
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-05-31
---

# [LKPR-54] lore_forget — explicit memory lifecycle control

## Problem

Agents have no way to clean up wrong memories. A hallucinated fact, duplicate, or outdated reference pollutes search results forever. The only path is `lore_update(useful=False)` → slow score decay → eventual soft-delete. For agents managing real stakes (autonomous agents handling money, compliance-sensitive contexts), this is a liability.

Stale memories erode trust in search results. Self-healing agents need an explicit cleanup mechanism.

## Solution

New MCP tool `lore_forget`:

- `lore_forget(memory_ids=[...], reason="duplicate|hallucinated|outdated|expired")`
- Immediate soft-delete (reuses existing soft-delete engine — no new infra)
- Logs `reason` for auditability
- No cascade — doesn't delete linked memories, just the target
- Future: `expired` could auto-clean time-bounded memories ("sprint-12-velocity was 8" is stale by sprint 14)

Minimal — the engine already supports soft-delete. This is just an MCP tool handler + reason logging + tests.

## Acceptance Criteria

- [ ] `lore_forget(memory_ids=["uuid1", "uuid2"])` soft-deletes those memories immediately
- [ ] `reason` parameter is logged (stored in memory metadata or separate audit log)
- [ ] Soft-deleted memories don't appear in `lore_search` results
- [ ] Existing `lore_update(useful=False)` path still works unchanged
- [ ] All existing tests pass

## Affected Files

**Backend:**

- `src/lorekeeper/handlers.py` — new `handle_lore_forget` handler
- `src/lorekeeper/services/memory_engine.py` — may need thin wrapper for soft-delete by ID
- `src/lorekeeper/schemas.py` — `LoreForgetParams` schema

**Dashboard (if applicable):**

- `_none_`

## Dependencies

_None_ — soft-delete already exists in the engine. Just need MCP tool handler + reason logging + tests.

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] Add `lore_forget` to tool reference
- **Skills**: [ ] `lorekeeper-search` — ensure search filters soft-deleted correctly (should already)
- **Backlog**: [ ] N/A

## Open Questions

- Should `lore_forget` be reversible? (No — soft-delete is reversible by design, but we won't expose an undelete in v1)
- Should we log the forgetting agent's identity? (Yes, if namespace tracking is available)

## Notes

Filed from daily product ideas cron. S-sized effort — mostly MCP plumbing. High hygiene value for agent trust. Not blocking current critical path (LKPR-29/30).
