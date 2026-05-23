---
id: LKPR-26
title: lore_insert silently errors with "'title'" when memory dict lacks required title field
type: bug
status: backlog
priority: high
sprint: ~
rice_score: ~
filed_by: Akane (PM)
filed_date: 2026-05-23
---

# [LKPR-26] lore_insert silently errors with "'title'" when memory dict lacks required title field

## Symptom

Calling `lore_insert(memories=[{"content": "...", "score": 8}])` — without a `title` key — returns:

```json
{
  "inserted_memories": [],
  "errors": [{"input": "", "error": "'title'"}]
}
```

The error `"'title'"` is a bare `KeyError` string, giving no indication that `title` is a required field. The tool call returns exit code 0 so the agent doesn't notice the failure — memories are silently dropped.

## Root Cause (confirmed)

`orchestrator.py` line 133 does `title = m["title"]` unconditionally — no `.get()`, no default, no validation. If the caller omits `title`, Python raises `KeyError: 'title'` which is caught by the outer `except Exception` and stringified as `"'title'"`.

The MCP tool signature (`server.py`) accepts `memories: list[dict]` with no documented schema for the dict — so the agent has no way to know `title` is required.

## Acceptance Criteria

- [ ] `_insert_one_memory` raises a descriptive `ValueError` if `title` is missing: `"memory dict missing required field: 'title'"`
- [ ] The error response includes that message — not a bare `"'title'"`
- [ ] MCP tool docstring / description documents that each memory dict must have `title` (required) and `content`, `score`, `description` (optional)
- [ ] Unit test: inserting a memory without `title` returns a clear error string in `errors[]`

## Affected Files

**Backend:**
- `src/lorekeeper/services/orchestrator.py` — add explicit validation before `m["title"]`
- `src/lorekeeper/server.py` — add docstring to `lore_insert` documenting memory dict schema

## Dependencies
_None_

## Open Questions
- Should we also validate `content` is present? Currently it defaults to `""` via `.get()` — probably fine.

## Notes
Distinct from LKPR-21 (`lore_update` field name inconsistency). This is a missing-field validation + unhelpful error message issue in `lore_insert`.
Filed after observing `lore_insert` calls failing silently during reflection (agent passed dicts without `title`).
