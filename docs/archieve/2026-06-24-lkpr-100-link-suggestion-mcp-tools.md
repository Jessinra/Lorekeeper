# LKPR-100 Implementation Plan — Link Suggestion MCP Tools

**Ticket:** LKPR-100 — MCP tools for link suggestion review  
**Date:** 2026-06-24  
**GitHub issue:** #232

---

## Problem

The LKPR-99 sweep engine populates `link_suggestions` with pending candidate pairs, but there are no MCP tools for agents to retrieve or act on them. Without `lore_get_suggestions` and `lore_review_suggestion`, the table is a write-only dead end.

---

## What We're Building

Two new MCP tools:

1. `lore_get_suggestions` — retrieve pending suggestions, sorted by quality, filtered by min_score
2. `lore_review_suggestion` — accept or reject one **or more** suggestions in a single call. Accept → create real link + set status='accepted'. Reject → set status='rejected'. Returns per-ID results + summary. Idempotent per-item.

---

## Affected Files (corrected from ticket)

The ticket lists `link_store.py` and `schemas.py`. Neither is correct:

- `schemas.py` does not exist — validation lives in server.py handler helpers
- Suggestion methods belong in `suggestion_store.py` (LKPR-99 already extracted `LinkSuggestionStore` there, not `link_store.py`)

Actual files to change:

| File                                                         | Change                                                                                                                   |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `src/lorekeeper/services/suggestion_store.py`                | Add `get_pending_suggestions()` + `count_pending_suggestions()`                                                          |
| `src/lorekeeper/services/orchestrator.py`                    | Add optional `suggestions` param to `__init__`; add `get_suggestions()` + `review_suggestion()`                          |
| `src/lorekeeper/server.py`                                   | Instantiate main-thread `LinkSuggestionStore`; pass to `MemoryService`; add 2 handler helpers + 2 MCP tool registrations |
| `src/lorekeeper/serializers.py`                              | Add `serialize_suggestion()`                                                                                             |
| `tests/_helpers.py`                                          | Update `build_service()` to pass `stores.suggestions`                                                                    |
| `tests/test_handlers.py`                                     | New `TestSuggestionTools` test class                                                                                     |
| `docs/api-reference.md`                                      | Document 2 new tools (table + full spec sections)                                                                        |
| `src/lorekeeper/assets/skills/lorekeeper-reconcile/SKILL.md` | Brief note on suggestion review workflow                                                                                 |

---

## Step-by-Step Implementation

### Step 1 — `suggestion_store.py`: two new query methods

```python
def get_pending_suggestions(
    self, limit: int = 20, min_score: float = 0.0
) -> list[LinkSuggestion]:
    """Return pending suggestions ordered by weighted_score DESC."""
    rows = self._conn.execute(
        """SELECT * FROM link_suggestions
           WHERE status = 'pending' AND weighted_score >= ?
           ORDER BY weighted_score DESC
           LIMIT ?""",
        (min_score, limit),
    ).fetchall()
    return [_row_to_suggestion(r) for r in rows]

def count_pending_suggestions(self) -> int:
    """Total count of pending suggestions (for workload display)."""
    row = self._conn.execute(
        "SELECT COUNT(*) FROM link_suggestions WHERE status = 'pending'"
    ).fetchone()
    return row[0] if row else 0
```

No changes to accept/reject — those already exist as `update_suggestion_status` and `delete_suggestion`. Accept path will use `update_suggestion_status` only (status → 'accepted'); no deletes.

---

### Step 2 — `orchestrator.py`: wire suggestions store + two public methods

#### Constructor change (backward-compatible, optional param):

```python
def __init__(
    self,
    engine: MemoryEngine,
    memories: MemoryStore,
    links: LinkStore,
    reflections: ReflectionStore,
    metrics: MetricsStore,
    config: ConfigStore,
    keyword_index: KeywordIndex,
    settings: Settings,
    link_candidate_generator: LinkCandidateGenerator | None = None,
    suggestions: LinkSuggestionStore | None = None,  # NEW
) -> None:
    ...
    self.suggestions = suggestions  # may be None if not wired (raises on use)
```

Add import: `from lorekeeper.services.suggestion_store import LinkSuggestionStore`

#### `get_suggestions()`:

```python
def get_suggestions(
    self, limit: int = 20, min_score: float = 0.0
) -> dict[str, Any]:
    if self.suggestions is None:
        raise RuntimeError("LinkSuggestionStore not configured on MemoryService")
    self._increment_metric("lore_get_suggestions")
    items = self.suggestions.get_pending_suggestions(limit=limit, min_score=min_score)
    total = self.suggestions.count_pending_suggestions()
    return {"suggestions": items, "total_pending": total}
```

#### `review_suggestion()`:

```python
def review_suggestion(
    self, suggestion_id: str, action: str
) -> dict[str, Any]:
    """Accept or reject a suggestion. Idempotent."""
    if self.suggestions is None:
        raise RuntimeError("LinkSuggestionStore not configured on MemoryService")
    self._increment_metric("lore_review_suggestion")

    sug = self.suggestions.get_suggestion(suggestion_id)

    if action == "accept":
        if sug is None:
            # Already accepted — idempotent no-op (suggestion row retained)
            return {
                "success": True, "action": "accept",
                "link_id": None,
                "message": "Suggestion already processed",
            }
        if sug.status == "rejected":
            # Accepting a rejected suggestion: un-reject + accept
            # (edge case — treat as accept)
            pass

        # Resolve relation_type — fall back to "references" if None/invalid
        rel_type = sug.suggested_type
        if rel_type not in RELATION_TYPES:
            rel_type = "references"

        link = self.links.insert_link(
            source_memory_id=sug.source_memory_id,
            target_memory_id=sug.target_memory_id,
            relation_type=rel_type,
            reason="Accepted from link suggestion sweep",
        )
        self.suggestions.update_suggestion_status(suggestion_id, "accepted")
        self._conn.commit()
        return {
            "success": True, "action": "accept",
            "link_id": link.id,
            "message": "Suggestion accepted, link created",
        }

    elif action == "reject":
        if sug is None:
            # Unknown ID — not found
            return {
                "success": True, "action": "reject",
                "link_id": None,
                "message": "Suggestion not found",
            }
        if sug.status == "rejected":
            # Idempotent — already rejected
            return {
                "success": True, "action": "reject",
                "link_id": None,
                "message": "Suggestion already rejected",
            }
        self.suggestions.update_suggestion_status(suggestion_id, "rejected")
        self._conn.commit()
        return {
            "success": True, "action": "reject",
            "link_id": None,
            "message": "Suggestion rejected",
        }
    else:
        raise ValueError(f"Unknown action {action!r}. Must be 'accept' or 'reject'")
```

Note: `RELATION_TYPES` import is already at the top of `orchestrator.py`.

---

### Step 3 — `server.py`: wire the store, handler helpers, MCP tools

#### In `init_service()` — create main-thread suggestions store and pass to MemoryService:

```python
suggestions = LinkSuggestionStore(db)  # main MCP thread's own store instance

svc = MemoryService(
    engine, memories, links, reflections, metrics, config, kw, s,
    link_candidate_generator=link_candidate_generator,
    suggestions=suggestions,  # NEW
)
```

Import: `from lorekeeper.services.suggestion_store import LinkSuggestionStore` (already imported for sweep; may need to add to main import block).

#### Handler helpers:

```python
_MAX_SUGGESTIONS_LIMIT = 100

def _handle_get_suggestions(
    svc: MemoryService,
    limit: int = 20,
    min_score: float = 0.0,
) -> dict[str, Any]:
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    limit = min(limit, _MAX_SUGGESTIONS_LIMIT)
    if not (0.0 <= min_score <= 1.0):
        raise ValueError("min_score must be between 0.0 and 1.0")
    result = svc.get_suggestions(limit=limit, min_score=min_score)
    from lorekeeper.serializers import serialize_suggestion
    serialized = [serialize_suggestion(s) for s in result["suggestions"]]
    return {
        "suggestions": serialized,
        "count": len(serialized),
        "total_pending": result["total_pending"],
    }


def _handle_review_suggestion(
    svc: MemoryService,
    suggestion_id: str,
    action: str,
) -> dict[str, Any]:
    if not suggestion_id or not suggestion_id.strip():
        raise ValueError("suggestion_id is required")
    if action not in {"accept", "reject"}:
        raise ValueError(f"action must be 'accept' or 'reject', got {action!r}")
    return svc.review_suggestion(suggestion_id=suggestion_id, action=action)
```

#### MCP tool registrations:

```python
@mcp.tool(name="lore_get_suggestions")
async def lore_get_suggestions(
    limit: int = 20,
    min_score: float = 0.0,
) -> dict[str, Any]:
    """Retrieve pending link suggestions for review.

    Args:
        limit: Max suggestions to return (default 20, max 100).
        min_score: Minimum weighted_score filter (default 0.0).
    """
    try:
        return _handle_get_suggestions(get_service(), limit=limit, min_score=min_score)
    except Exception:
        log.exception("lore_get_suggestions_failed")
        raise


@mcp.tool(name="lore_review_suggestion")
async def lore_review_suggestion(
    suggestion_id: str,
    action: str,
) -> dict[str, Any]:
    """Accept or reject a link suggestion.

    On accept: creates a real memory_links row and sets status='accepted' (suggestion row retained for audit trail).
    On reject: marks the suggestion as rejected (future sweeps skip this pair).
    Idempotent — double-accept and double-reject both return success.

    Args:
        suggestion_id: The suggestion UUID.
        action: Either 'accept' or 'reject'.
    """
    try:
        return _handle_review_suggestion(
            get_service(), suggestion_id=suggestion_id, action=action
        )
    except Exception:
        log.exception("lore_review_suggestion_failed", suggestion_id=suggestion_id)
        raise
```

---

### Step 4 — `serializers.py`: `serialize_suggestion()`

```python
from lorekeeper.models import LinkSuggestion  # add to imports

def serialize_suggestion(suggestion: LinkSuggestion) -> dict[str, Any]:
    """Serialize a LinkSuggestion for MCP response."""
    return {
        "id": suggestion.id,
        "source_memory_id": suggestion.source_memory_id,
        "source_title": suggestion.source_title,
        "target_memory_id": suggestion.target_memory_id,
        "target_title": suggestion.target_title,
        "weighted_score": round(suggestion.weighted_score, 4),
        "cosine_score": round(suggestion.cosine_score, 4),
        "bm25_score": round(suggestion.bm25_score, 4),
        "entity_score": round(suggestion.entity_score, 4),
        "temporal_score": round(suggestion.temporal_score, 4),
        "suggested_type": suggestion.suggested_type,
        "created_at": suggestion.created_at,
    }
```

---

### Step 5 — `tests/_helpers.py`: pass suggestions to build_service

```python
def build_service(
    stores: Stores,
    engine: Any,
    kw: KeywordIndex,
    settings: Settings,
) -> MemoryService:
    return MemoryService(
        engine,
        stores.memories,
        stores.links,
        stores.reflections,
        stores.metrics,
        stores.config,
        kw,
        settings,
        suggestions=stores.suggestions,  # NEW — wired so new MCP tools work in tests
    )
```

This is backward-compatible — all existing tests continue to work (they don't call suggestion methods, so `self.suggestions` being present causes no issues).

---

### Step 6 — `tests/test_handlers.py`: new test class

Add `TestSuggestionTools` class covering:

**`_handle_get_suggestions` tests:**

- `test_get_suggestions_empty` — empty table returns `{suggestions: [], count: 0, total_pending: 0}`
- `test_get_suggestions_returns_pending_sorted` — multiple pending suggestions, verify sorted by weighted_score DESC
- `test_get_suggestions_min_score_filter` — only returns suggestions at or above min_score
- `test_get_suggestions_limit_capped_at_100` — passing limit=200 is capped to 100
- `test_get_suggestions_skips_rejected` — rejected rows not returned
- `test_get_suggestions_invalid_limit_raises` — limit=0 or limit=-1 raises ValueError
- `test_get_suggestions_invalid_min_score_raises` — min_score=-0.1 or 1.5 raises ValueError
- `test_get_suggestions_total_pending_counts_all` — total_pending reflects full table, not just the page

**`_handle_review_suggestion` tests:**

- `test_review_accept_creates_link_sets_accepted_status` — accept: link exists, suggestion row has status='accepted'
- `test_review_accept_sets_correct_relation_type` — suggested_type flows through to link
- `test_review_accept_falls_back_to_references_for_invalid_type` — bad type → "references"
- `test_review_accept_idempotent` — double-accept returns success, no error
- `test_review_reject_sets_status_rejected` — suggestion row has status='rejected'
- `test_review_reject_idempotent` — double-reject returns success
- `test_review_suggestion_invalid_action_raises` — "approve" raises ValueError
- `test_review_suggestion_empty_id_raises` — empty string raises ValueError

---

### Step 7 — `docs/api-reference.md`: document new tools

Update the tools table (8 tools → 10 tools) and add full spec sections for both tools.

---

### Step 8 — `lorekeeper-reconcile/SKILL.md`: brief workflow note

Add a section noting that agents can call `lore_get_suggestions` to retrieve sweep-generated candidates and `lore_review_suggestion` to accept or reject them, as part of the memory graph maintenance workflow.

---

## Edge Cases and Decisions

| Case                                                           | Decision                                                                       |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `accept` on suggestion already at status='accepted'            | Return `success=True`, `link_id=None`, "already processed" — idempotent no-op  |
| `accept` on rejected suggestion                                | Treat as accept — create link, set status='accepted'                           |
| `reject` on missing suggestion                                 | Return `success=True`, message "already processed"                             |
| `reject` on already-rejected suggestion                        | Return `success=True`, no-op                                                   |
| `suggested_type` is None or not in RELATION_TYPES              | Fall back to `"references"`                                                    |
| `insert_link` raises FK violation (memory deleted after sweep) | Let it propagate — surface as structured error via server.py exception handler |
| `suggestions` is None on MemoryService                         | RuntimeError — misconfiguration, surfaces immediately                          |
| `limit` > 100                                                  | Silently capped at 100 (defensive, same pattern as other tools)                |

---

## Test Plan Verification Mapping

| AC                                                              | Test                                                                                                                               |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `lore_get_suggestions` implemented with `limit` and `min_score` | `test_get_suggestions_returns_pending_sorted`, `test_get_suggestions_min_score_filter`, `test_get_suggestions_limit_capped_at_100` |
| `lore_review_suggestion` implemented                            | `test_review_accept_creates_link_sets_accepted_status`, `test_review_reject_sets_status_rejected`                                  |
| Accept creates link + sets status='accepted'                    | `test_review_accept_creates_link_sets_accepted_status`                                                                             |
| Reject sets status='rejected'                                   | `test_review_reject_sets_status_rejected`                                                                                          |
| Idempotent                                                      | `test_review_accept_idempotent`, `test_review_reject_idempotent`                                                                   |
| Metric counter incremented                                      | verified via `MetricsStore` in integration test                                                                                    |
| Existing tests pass                                             | full suite run before push                                                                                                         |
| No LLM calls                                                    | pure DB ops — no engine calls in any new code path                                                                                 |

---

## Order of Execution

1. `suggestion_store.py` — new query methods (no deps)
2. `orchestrator.py` — wire store + new methods (depends on step 1)
3. `serializers.py` — serialize_suggestion (no deps)
4. `tests/_helpers.py` — pass suggestions (no deps)
5. `server.py` — handler helpers + MCP registrations (depends on 1-4)
6. `tests/test_handlers.py` — tests (depends on all above)
7. `docs/api-reference.md` — docs
8. `lorekeeper-reconcile/SKILL.md` — workflow note
9. Run full test suite
10. Self-review (score ≥ 8 gate)

---

## Boundary with LKPR-101

LKPR-101 is the dashboard UI for these operations. This ticket is MCP-layer only — no dashboard changes.
