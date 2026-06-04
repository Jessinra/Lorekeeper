---
id: LKPR-10
title: Multi-agent tenancy with namespace isolation
type: feature
sprint: deferred
rice_score: 8.4 # R:4 I:7 C:30% E:4w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-10] Multi-agent tenancy with namespace isolation

## Problem

When a second Hermes agent (work laptop) comes online, both agents will share the same memory store. No namespace isolation, no conflict resolution when both agents insert about the same topic, no access control between personal and work memories.

## Solution

- Add `namespace` field to all memories (e.g. `personal`, `work`, `shared`)
- Default namespace per agent configurable via `LORE_NAMESPACE` env var
- `lore_search`: optional `namespace` filter param
- `lore_insert`: auto-tags with agent's namespace
- Shared memories: explicit `shared` namespace visible to all agents
- Conflict resolution: flag near-duplicate memories across namespaces for review rather than auto-merge

## Acceptance Criteria

- [ ] All memories have a `namespace` field (schema migration included)
- [ ] `lore_insert` auto-tags with `LORE_NAMESPACE` env var value
- [ ] `lore_search` accepts optional `namespace` filter
- [ ] Dashboard shows namespace filter in UI
- [ ] Migration script handles existing memories (default to `personal`)

## Affected Files

- `src/lorekeeper/models.py` — add namespace field + SQLite migration
- `src/lorekeeper/services/search.py` — namespace filter
- `src/lorekeeper/services/orchestrator.py` — namespace-aware insert/dedup
- `src/lorekeeper/config.py` — `LORE_NAMESPACE` env var
- Dashboard — namespace filter in UI

## Dependencies

_None_ (but don't build until the trigger condition is met)

## Open Questions

_None_

## Notes

**ABSORBED INTO LKPR-38** (2026-05-27) — approach shifted from env-var-per-agent to server-side token resolution. LKPR-38 covers the core namespace plumbing, LKPR-39 adds token management, LKPR-40 adds RBAC.

The original deferred note is no longer valid — the trigger condition (multiple Hermes profiles) is active: Bella + Diana + Akane all on the same Lorekeeper DB. Building now.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
