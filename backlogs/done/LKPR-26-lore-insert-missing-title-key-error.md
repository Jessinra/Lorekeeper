---
id: LKPR-26
title: lore_insert returns unhelpful "'title'" error when memory dict is missing required title field
type: chore
sprint: ~
rice_score: ~
filed_by: Akane (PM)
filed_date: 2026-05-23
resolved_date: 2026-05-23
---

# [LKPR-26] lore_insert returns unhelpful "'title'" error when memory dict is missing required title field

## Problem

## Symptom

Calling `lore_insert(memories=[{"content": "...", "score": 8}])` — without a `title` key

## Solution

Add explicit validation in `orchestrator.py::_insert_one_memory` before the unconditional `m["title"]` access. If `title` is missing, raise a descriptive `ValueError` with the message `"memory dict missing required field: 'title'"` rather than letting Python raise a bare `KeyError`. Also update the MCP tool docstring in `server.py` to document that each memory dict must have `title` (required) and `content`, `score`, `description` (optional).

No code logic change — the error message is the fix.

Returns:

```json
{
  "inserted_memories": [],
  "errors": [{ "input": "", "error": "'title'" }]
}
```

The error `"'title'"` is a bare `KeyError` string, giving no indication that `title` is a required field. The tool call returns exit code 0 so the agent doesn't notice the failure — memories are silently dropped.

## Root Cause (confirmed)

`orchestrator.py` line 133 does `title = m["title"]` unconditionally. If the caller omits `title`, Python raises `KeyError: 'title'` caught by the outer `except Exception` and stringified as `"'title'"`.

**Note:** This is primarily a caller error — `title` is documented as required in the `lorekeeper-memorize` skill. The code behaviour is correct; the error message is just unhelpful.

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

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
