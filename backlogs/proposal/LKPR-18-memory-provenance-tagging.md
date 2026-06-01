---
id: LKPR-18
title: Memory Metadata — Provenance Tagging + Agent Tags
type: feature
status: S:proposal
priority: P2:medium
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-05-22
updated_date: 2026-06-01
---

# [LKPR-18] Memory Metadata — Provenance Tagging + Agent Tags

## Problem

Agents have no way to introspect or scope memories by origin:
1. **Provenance**: no way to know where a memory came from — was it extracted, inferred, manually inserted, or synthesized? Without provenance, trust calibration is impossible.
2. **Agent scoping**: in multi-agent environments (Akane + Bella + work agent), memories from different agents mix in the same namespace. No way to say "show me only memories from this project" or "only from the work agent." Shared memory without filtering becomes increasingly noisy.

## Solution

Extend memory metadata with two orthogonal fields stored in SQLite:

Phase A — Provenance (`source_type`): tag every memory at write time:
- `observed` — extracted from conversation
- `inferred` — agent derived it
- `user_stated` — user said it explicitly
- `consolidated` — merged from multiple memories
- `injected` — manually added

Phase B — Agent tags (`tags`): optional key-value dict on `lore_insert`/`lore_remember`. No new MCP tools — extend existing schemas. Example: `lore_insert(..., tags={"agent": "claude-code", "project": "lorekeeper"})` with `lore_search(..., tags_filter={"agent": "claude-code"})`. Tags are passive metadata — not scoring factors, not required.

Both phases use the same SQLite metadata column; can ship together or separately.

## Acceptance Criteria

- [ ] [Provenance] `lore_insert` accepts optional `source_type` param (defaults to `observed`)
- [ ] [Provenance] `source_type` stored in SQLite metadata and returned in `lore_search` results
- [ ] [Provenance] `lore_search` supports `source_type` filter
- [ ] [Provenance] Existing memories backfilled with `source_type: unknown`
- [ ] [Provenance] Schema migration handles existing data without data loss
- [ ] [Tags] `lore_insert` and `lore_remember` accept optional `tags` dict (key-value pairs)
- [ ] [Tags] `tags` stored in SQLite metadata table
- [ ] [Tags] `lore_search` supports `tags_filter` param (dict; returns memories matching ALL specified tags)
- [ ] [Tags] Tags returned in search results alongside existing metadata
- [ ] [Tags] No schema changes if `tags` not provided (backward compatible)

## Affected Files

**Backend:**

- `src/lorekeeper/models.py` — add `source_type` and `tags` fields
- `src/lorekeeper/services/memory_engine.py` — persist at insert time
- `src/lorekeeper/services/search.py` — return + filter on both fields
- `src/lorekeeper/handlers.py` — expose in tool inputs/outputs
- `scripts/migrate_from_json.py` — backfill `source_type: unknown`, `tags: {}`

**Dashboard (if applicable):**

- `_none_`

## Dependencies

_None_

## Open Questions

- Should `source_type` be an enum (strict) or free-string (flexible)? Lean toward enum for v1.
- Tags filter: AND semantics (all tags must match) vs OR? Start with AND — simpler.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
