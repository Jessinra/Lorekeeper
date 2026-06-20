---
id: LKPR-100
title: MCP tools for link suggestion review — get suggestions and accept/reject
type: feature
sprint: ~
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

Accept or reject a specific suggestion. Idempotent — calling accept on an already-accepted suggestion returns success (no-op). Rejecting a rejected suggestion is also a no-op.

**Input:**

- `suggestion_id` (str, required) — the suggestion UUID
- `action` (str, required) — either `"accept"` or `"reject"`

**On accept:** Creates a real `memory_links` row using the candidate's `suggested_type` (from the new Phase 1 type set in LKPR-99), then deletes the suggestion row from `link_suggestions`.

**On reject:** Sets `status='rejected'` on the suggestion. Future sweeps will skip this pair.

**Output:**

```json
{
  "success": true,
  "action": "accept",
  "link_id": "uuid" | null,  // link id if accepted, null if rejected
  "message": "Suggestion accepted, link created"
}
```

### Batch operations

Both tools work on individual suggestions. For batch operations (bulk-accept top-N, bulk-reject all below threshold), the agent calls these in a loop over however many items it can fit in one turn. If batch endpoints prove necessary, they can be added as a follow-up.

### Server-side hooks

- `lore_review_suggestion` increments a `lore_review_suggestion` metric counter
- Errors surface as structured responses, not raw exceptions

## Acceptance Criteria

- [ ] `lore_get_suggestions` MCP tool implemented with `limit` and `min_score` params
- [ ] `lore_review_suggestion` MCP tool implemented with `suggestion_id` and `action`
- [ ] Accept creates a real `memory_links` row and removes suggestion
- [ ] Reject sets status to `rejected` (no link created)
- [ ] Idempotent: no-op on double-accept or double-reject
- [ ] Metric counter incremented on review actions
- [ ] All existing tests pass; new tests for both tools (input validation + integration)
- [ ] No LLM calls — pure DB operations

## Affected Files

- `src/lorekeeper/server.py` — register `lore_get_suggestions` and `lore_review_suggestion` MCP tools
- `src/lorekeeper/services/orchestrator.py` — `get_suggestions()`, `review_suggestion()` methods
- `src/lorekeeper/services/link_store.py` — `get_pending_suggestions()`, `accept_suggestion()`, `reject_suggestion()`
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
