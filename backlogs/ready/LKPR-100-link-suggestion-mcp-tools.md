---
id: LKPR-100
title: MCP tools for link suggestion review — get suggestions and accept/reject
type: feature
sprint: 4
rice_score: ~
filed_by: Akane
github_issue: 232
filed_date: 2026-06-20
---

# [LKPR-100] MCP tools for link suggestion review — get suggestions and accept/reject

## Problem

Once the sweep engine (LKPR-99) populates the `link_suggestions` table with pending candidates, agents need a way to retrieve and act on them. No MCP tool currently exists for batch suggestion review.

Without these tools, suggestions sit in the DB forever — agents can't discover or act on them programmatically.

## Solution

Two new MCP tools on the Lorekeeper server:

### 1. `lore_get_suggestions`

Retrieve pending link suggestions for review.

**Input:**

- `limit` (int, optional, default 20, max 100) — max suggestions to return
- `min_score` (float, optional, default 0.0) — minimum weighted_score filter

**Output:**

```json
{
  "suggestions": [
    {
      "id": "uuid",
      "source_memory_id": "...",
      "source_title": "...",
      "target_memory_id": "...",
      "target_title": "...",
      "weighted_score": 0.72,
      "cosine_score": 0.81,
      "bm25_score": 0.65,
      "entity_score": 0.3,
      "temporal_score": 0.55,
      "suggested_type": "references",
      "created_at": "2026-06-20T12:00:00"
    }
  ],
  "count": 20,
  "total_pending": 142
}
```

- Sorted by `weighted_score DESC` (best candidates first)
- Only returns `status='pending'` suggestions
- `total_pending` gives agents a sense of workload without a separate count call

### 2. `lore_review_suggestion`

Accept or reject one or more suggestions in a single call. Each item is processed independently — a failure on one does not abort the rest. Idempotent per item — calling accept on an already-accepted suggestion returns `status='skipped'`, and double-reject does the same.

**Input:**

- `suggestion_ids` (list[str], required) — one or more suggestion UUIDs
- `action` (str, required) — either `"accept"` or `"reject"`

**On accept:** Creates a real `memory_links` row using the candidate's `suggested_type` (falls back to `'references'` if None or unrecognised). Suggestion row is retained with `status='accepted'` for audit trail (not deleted).

**On reject:** Sets `status='rejected'` on the suggestion. Future sweeps will skip this pair.

**Output:**

```json
{
  "results": [
    {"id": "uuid", "status": "accepted"|"rejected"|"skipped", "link_id": "uuid"|null, "message": "..."}
  ],
  "accepted": 1,
  "rejected": 0,
  "skipped": 0,
  "errors": []
}
```

### Batch operations

`lore_review_suggestion` accepts a `list[str]` — bulk-accept or bulk-reject any number of suggestions in a single call. Items are processed independently; partial success is reported per-item in `results`.

### Server-side hooks

- `lore_review_suggestion` increments a `lore_review_suggestion` metric counter
- `lore_get_suggestions` increments a `lore_get_suggestions` metric counter
- Errors surface as structured responses, not raw exceptions
- Suggestion logic lives in `server.py` handler helpers directly — **not routed through `MemoryService`**; `LinkSuggestionStore` is a module-level singleton on `server.py` (same DB, main thread)

## Acceptance Criteria

- [ ] `lore_get_suggestions` MCP tool implemented with `limit` and `min_score` params
- [ ] `lore_review_suggestion` MCP tool implemented with `suggestion_ids` (list[str]) and `action`
- [ ] Accept creates a real `memory_links` row; suggestion retained with `status='accepted'`
- [ ] Reject sets status to `rejected` (no link created); suggestion retained for audit
- [ ] Idempotent: double-accept and double-reject both return `status='skipped'`
- [ ] Batch: multiple IDs processed independently in one call; partial success supported
- [ ] Metric counter incremented on both tools
- [ ] `LinkSuggestionStore` is NOT a member of `MemoryService` — wired separately in `server.py`
- [ ] All existing tests pass; new tests for both tools (input validation + integration)
- [ ] `test_handlers.py` restored with all original tests plus `TestSuggestionHandlers`
- [ ] No LLM calls — pure DB operations

## Affected Files

- `src/lorekeeper/server.py` — register MCP tools + standalone handler helpers; module-level `_suggestions_store`
- `src/lorekeeper/services/suggestion_store.py` — `get_pending_suggestions()`, `update_suggestion_status()`
- `src/lorekeeper/schemas.py` — input/output schemas for new tools
- `src/lorekeeper/serializers.py` — suggestion serialization
- `tests/test_handlers.py` — new test cases

## Dependencies

- LKPR-99 (link suggestion sweep engine) — provides the `link_suggestions` table and data

## Required Updates

- **docs/api-reference.md**: [ ] Document two new MCP tools
- **Skills**: [ ] `lorekeeper-reconcile` — note suggestion review workflow

## Notes

Split from LKPR-98 (combined meta-ticket). Dashboard UI for these operations is a separate ticket (LKPR-101).
