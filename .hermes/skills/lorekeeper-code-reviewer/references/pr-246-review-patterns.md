# PR #246 (LKPR-100) — Review Patterns

**PR:** #246 — Add `lore_get_suggestions` + `lore_review_suggestion` MCP tools  
**Branch:** `feat/lkpr-100-link-suggestion-mcp-tools`  
**Date:** 2026-06-25

## What shipped

Two new MCP tools exposing the LKPR-99 sweep engine's `link_suggestions` table:

- `lore_get_suggestions(limit, min_score)` — list pending candidates sorted by `weighted_score DESC`
- `lore_review_suggestion(suggestion_ids: list[str], action)` — batch accept/reject; per-item independent; idempotent

Architecture: `LinkSuggestionStore` wired as a module-level singleton on `server.py` (`_suggestions_store`), NOT on `MemoryService`. This correctly enforces the MemoryService/SweepService boundary (guarded by `test_memory_service_has_no_suggestions_attr`).

## Issues found in this review

### 1. Deferred import inside hot loop (MAJOR)

**Location:** `server.py:667`

```python
for sid in cleaned:
    if action == "accept":
        ...
        from lorekeeper.models import RELATION_TYPES   # ← inside loop
        rel_type = sug.suggested_type
        if rel_type not in RELATION_TYPES:
```

`RELATION_TYPES` is importable at module level (`lorekeeper.models` is already imported in `server.py`). The loop import runs N times for a batch. Fix: move to module-level imports at line 8.

**Pattern to generalise:** Any `from X import Y` inside a `for` loop body is a smell in hot paths. Ruff doesn't catch this. Reviewers must scan manually.

### 2. Redundant method pair — `all_pending_suggestions()` vs `get_pending_suggestions()` (MAJOR)

**Location:** `suggestion_store.py:185`

`get_pending_suggestions(limit, min_score)` added by this PR is a strict superset of `all_pending_suggestions()` (same query, no limit/filter). The older method is only called in two test files. Per Jason's explicit principle (remove unused infra), `all_pending_suggestions()` should be removed and the two test callsites migrated.

**Detection command:**

```bash
grep -rn "all_pending_suggestions" src/ tests/
```

### 3. Missed AC — `lorekeeper-reconcile` SKILL.md not updated (MAJOR)

**Ticket AC (Required Updates):**

> Skills: `lorekeeper-reconcile` — note suggestion review workflow

The diff showed zero changes to `src/lorekeeper/assets/skills/lorekeeper-reconcile/SKILL.md`. The AC was explicit. This is the pattern: ticket Required Updates sections contain skill/doc update obligations that are just as mandatory as code ACs.

**Detection step added to review checklist:** Step 4a — scan all `- [ ]` AC checkboxes AND the "Required Updates" section for skill/doc obligations before marking code review complete.

### 4. API docs missing `status: "error"` value (MINOR)

**Location:** `docs/api-reference.md` — `lore_review_suggestion` response schema

The implementation appends `status: "error"` to `results` for per-item exceptions, and also appends to the `errors` list (dual reporting). The docs only listed `"accepted" | "rejected" | "skipped"`. Callers doing exhaustive match on `status` would fail on `"error"`.

### 5. `build_service()` silently drops `stores.suggestions` (MINOR)

`Stores` dataclass includes `suggestions: LinkSuggestionStore` but `build_service()` never passes it to `MemoryService` (correct by design — the boundary test enforces this). A comment explaining why it's intentionally omitted would prevent future "am I missing a wiring call?" confusion.

## What was done well

- `isinstance(limit, bool)` guard — `bool` subclasses `int`; most code misses this
- `svc.commit()` only on `if accepted or rejected` — skips fsync for all-skip batches
- `test_review_accept_on_rejected_creates_link` — covers the accept-on-rejected edge case
- Restoring all 40 original `test_handlers.py` tests + 25 new = solid net-positive delta
- Full 436-test suite passing, ruff clean
