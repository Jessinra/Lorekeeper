# Step 4a — SuggestionProcessor: kill the duplicated batch loop

**Branch:** `chore/lkpr-105-step4a-suggestion-processor`
**Depends on:** Step 2 only (can run before/parallel to Step 3)
**Files:** 2 new, 3 modified, exception entries deleted
**Behavior change:** ONE deliberate unification (see below) — flag for Akane in PR

## Why first among processors

`handle_review_suggestion` (MCP) and `batch_suggestions` (dashboard) implement
the same accept/reject loop twice with divergent semantics:

| Divergence              | MCP handler                   | Dashboard route                    | Unified (MCP wins) |
| ----------------------- | ----------------------------- | ---------------------------------- | ------------------ |
| Suggestion not found    | `skipped`                     | `error`                            | `skipped`          |
| Commit                  | only if accepted/rejected > 0 | unconditional                      | conditional        |
| Accept already-accepted | skipped                       | not re-checked (relies on service) | skipped            |

## Changes

### 1. NEW `src/lorekeeper/processors/__init__.py` (empty)

### 2. NEW `src/lorekeeper/processors/suggestion.py` — `SuggestionProcessor`

```python
class SuggestionProcessor:
    def __init__(self, suggestion_service: SuggestionService,
                 suggestions: LinkSuggestionStore,
                 metrics: MetricsStore, db: Database) -> None: ...

    def recommend_links(self, lore_id: str, top_k: int | None) -> list[LinkCandidate]:
        # validation from handle_recommend_links: lore_id non-empty,
        # top_k positive int (bool-guard), cap 50; metric increment
    def get_pending(self, limit: int, min_score: float) -> tuple[list[LinkSuggestion], int]:
        # validation from handle_get_suggestions: limit positive int cap 100,
        # 0.0 <= min_score <= 1.0; metric; returns (items, total_pending)
    def review(self, suggestion_ids: list[str], action: str) -> ReviewResult:
        # THE single batch loop — move handle_review_suggestion's body
        # verbatim (it is the richer of the two). Returns a plain dataclass
        # ReviewResult(results, accepted, rejected, skipped, errors) with
        # per-item dicts {id, status, link_id, message}. NO serialization.
        # RELATION_TYPES fallback-to-"references" logic comes along.
        # Conditional db.commit() at the end.
```

Until Step 3b lands, the processor reaches services via the facade instance
passed at construction time in `server.py` (`svc.suggestion_service`) — the
processor's own constructor signature is final from day one; only the wiring
site changes later. Processors import domains/platform/infra only — no new
architecture exceptions.

### 3. `api/mcp/handlers/suggestion_handlers.py` — gut to shims

- `handle_recommend_links(processor, lore_id, top_k)` → call + serialize
- `handle_get_suggestions(processor, limit, min_score)` → call + serialize
- `handle_review_suggestion(processor, suggestion_ids, action)` → call +
  return dataclass as dict (shape already matches MCP output — verify against
  `docs/plans/lkpr-104-mcp-baseline.json`)
- Delete the `MemoryService` TYPE_CHECKING import and the batch loop.

### 4. `dashboard/routes/suggestions.py` — `batch_suggestions` delegates

Call `get_suggestion_processor().review(body.suggestion_ids, action)`, map
`ReviewResult` into the existing `BatchResponse`/`BatchResultItem` Pydantic
models (response SHAPE unchanged). Not-found items now map to
status="skipped" — this is the unification; document in PR description with
the option of a `strict_not_found` flag if Akane wants old behavior.
`trigger_sweep`/`sweep_status` untouched (Step 4d).

### 5. `server.py`

Construct `SuggestionProcessor` in `init_service()`; add
`get_suggestion_processor()` getter; rewire the three MCP tool bodies.
`get_suggestions_store()` stays for now (other callers) — dies in 4d/5.

### 6. Tests

- NEW `tests/processors/test_suggestion_processor.py`: move the review-loop
  test logic from `tests/test_handlers.py` review tests (keep handler-level
  smoke tests that the MCP envelope still works); add one regression test
  pinning the unified semantics: not-found → skipped, no commit when nothing
  changed (assert via db spy or connection total_changes).
- `tests/test_dashboard.py` batch tests: update the not-found expectation
  (error → skipped) — the ONLY test-logic change in this step; call it out
  in the PR.

## Verification

```
uv run pytest tests/processors/ tests/test_handlers.py tests/test_dashboard.py -v
uv run pytest -q --ignore=tests/e2e
uv run pytest tests/test_architecture.py -v
uv run ruff check src tests scripts/ && uv run mypy src
grep -c "for sid in" src/lorekeeper/api/mcp/handlers/suggestion_handlers.py src/lorekeeper/dashboard/routes/suggestions.py  # both 0
```

MCP contract check: diff tool output shapes against
`docs/plans/lkpr-104-mcp-baseline.json` for the three suggestion tools.

## AC

- [ ] Batch loop exists exactly once, in `SuggestionProcessor.review`
- [ ] MCP output byte-identical to baseline
- [ ] Dashboard response shape unchanged; semantics unification documented in PR
- [ ] Suggestion-handler exception entries deleted
