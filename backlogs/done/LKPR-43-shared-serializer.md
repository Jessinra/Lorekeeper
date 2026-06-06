---
id: LKPR-43
github_issue: 81
title: Shared serializer for MCP + dashboard responses
type: enhancement
sprint: 2
rice_score: ~ # TBD: R:6 I:7 C:90% E:0.3w
filed_by: Diana
filed_date: 2026-05-27
---

# [LKPR-43] Shared serializer for MCP + dashboard responses

## Problem

Search result serialization lives in two places:

- `handlers.py` — `_result_to_dict()` for MCP tools (`lore_search`)
- `dashboard/app.py` — inline dict construction in `/api/search`

They've already drifted. The dashboard endpoint truncates content to 300 chars and omits `decay_factor`. The MCP endpoint returns full content and includes `decay_factor`. Every new field on `SearchResult`, `Memory`, or `MemoryLink` means touching at least 2 files, and they'll drift again.

Same pattern repeats for `/api/memories` and `/api/links` — both build their own response dicts inline.

## Solution

Move shared serialization into `src/lorekeeper/serializers.py` with one function per model. Callers pass optional kwargs for per-endpoint overrides (truncation, field exclusion).

```python
def serialize_search_result(
    result: SearchResult,
    *,
    truncate_content: int | None = None,
    exclude_fields: set[str] | None = None,
) -> dict:
    ...
```

No behavioral changes — each endpoint keeps its exact current output shape. The only change is where the code lives and how it's composed.

## Acceptance Criteria

- [ ] `src/lorekeeper/serializers.py` exists with `serialize_search_result()` and `serialize_memory()`
- [ ] `handlers.handle_search()` calls the shared serializer
- [ ] Dashboard `/api/search` calls the shared serializer with endpoint-specific overrides (truncation + exclude)
- [ ] All 87 existing tests pass unchanged

## Affected Files

- `src/lorekeeper/serializers.py` — new file
- `src/lorekeeper/handlers.py` — remove `_result_to_dict`, replace with import + call
- `src/lorekeeper/dashboard/app.py` — replace inline dict in `/api/search` with shared serializer call

## Dependencies

None

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Notes

This is "boring" infrastructure — no new capability, no user-facing change. But it eliminates a recurring friction point: every time I add a field to a response model, I touch one file, verify it, and move on. Currently I touch two and wonder if they match.

Estimated effort: ~1-2 days. Mostly moving code + updating imports + test verification.
