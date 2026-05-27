---
id: LKPR-38
title: Namespace env var + auto-scoping (foundation)
type: feature
status: S:done
priority: P1:high
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-05-27
replaces: LKPR-10
---

# [LKPR-38] Namespace env var + auto-scoping (foundation)

## Problem

All agents see every memory — Bella, Diana, Akane all query the same flat store. No isolation means work notes, personal reflections, and agent-specific knowledge are mixed. Need a dead-simple namespace layer before we add auth.

## Solution

**Declare namespace via env var** when setting up the MCP server connection. No tokens, no auth, no agent control — it's purely a setup-time configuration.

**How it works:**

1. **New env var:** `LORE_NAMESPACE` (default empty = `"shared"`)
   - `setup.sh` auto-injects per agent: Bella gets `LORE_NAMESPACE=bella`, Diana gets `LORE_NAMESPACE=diana`, etc.
   - Agent never configures or touches it within conversation — setup only

2. **Schema:** Add `namespace TEXT` column to SQLite memory table
   - Default value `"shared"` for backward compat
   - Existing memories get re-indexed as `"shared"` on migration

3. **Auto-scope all operations (server-side):**
   - **Insert** (`lore_insert`, `lore_remember`): auto-tags with agent's `LORE_NAMESPACE`
   - **Search** (`lore_search`): automatically queries union of **agent's namespace + `"shared"`**
   - Agent never passes a namespace parameter — invisible, no control

4. **No auth enforcement in this phase.** The namespace is a tag/filter, not a security boundary. Any agent could set `LORE_NAMESPACE=bella` and see Bella's namespace — that's fine for now. Auth comes in Ticket 2.

5. **Backward compatibility:**
   - No `LORE_NAMESPACE` set → all memories tagged `"shared"` → search returns everything (existing behavior)
   - Migration: existing memories get `namespace="shared"`

## Acceptance Criteria

- [ ] `LORE_NAMESPACE` env var parsed at server startup
- [ ] Connection context stores the namespace
- [ ] `lore_insert` / `lore_remember` auto-tags with connection's namespace
- [ ] `lore_search` auto-filters to `[agent_namespace, "shared"]` union
- [ ] No env var = `"shared"` (existing behavior preserved)
- [ ] SQLite migration: add `namespace TEXT DEFAULT "shared"`
- [ ] Existing memories backfilled to `namespace="shared"`
- [ ] Dashboard shows namespace in memory detail view
- [ ] `setup.sh` updated to inject `LORE_NAMESPACE` per agent profile

## Affected Files

- `src/lorekeeper/services/orchestrator.py` — connection context, namespace injection
- `src/lorekeeper/services/memory_engine.py` — namespace on store
- `src/lorekeeper/services/search.py` — [personal + shared] filter
- `src/lorekeeper/models.py` — namespace column + migration
- `src/lorekeeper/config.py` — `LORE_NAMESPACE` env var
- `scripts/setup.sh` — auto-inject per profile
- Dashboard — namespace in memory view

## Dependencies

None — this is the foundation.

## Open Questions

- Should `lore_update` and `lore_reflect` also auto-scope? (Yes — all write operations scoped to agent's namespace)
- What about `lore_insert` with explicit `namespace` param? (Not yet — agent has no control in this phase. That comes with ticket 3's multi-namespace RBAC)

## Notes

This is intentionally the simplest possible thing. No tokens, no auth, no management API. The namespace is a filter tag — nobody's locked out, nobody's authorized. The security boundary comes in Ticket 2 (LKPR-39).

Replaces and absorbs LKPR-10.

## Required Updates

- **CLAUDE.md**: [ ] add `LORE_NAMESPACE` docs
- **README.md**: [ ] add setup docs
- **Skills**: [ ] update `lorekeeper-search` / `lorekeeper-memorize` for auto-scoped search
- **Backlog**: [x] absorb LKPR-10