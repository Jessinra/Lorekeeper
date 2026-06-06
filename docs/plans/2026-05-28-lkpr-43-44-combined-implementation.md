# Combined Implementation Plan: LKPR-43 + LKPR-44

**PR:** Single branch implementing both tickets.
**Goal:** Shared serialization for MCP + dashboard responses (LKPR-43) + validate config overrides at startup (LKPR-44).

---

## LKPR-43 — Shared Serializer

**Problem:** `_result_to_dict()` in `handlers.py` and inline dict construction in `dashboard/app.py` `/api/search` duplicate the same serialization logic. They've already drifted (dashboard truncates content to 300, omits `decay_factor` and `confidence`/`created_at`/`updated_at`). Any new field on `Memory`/`MemoryLink`/`SearchResult` requires touching both.

**Solution:** Move serialization into `src/lorekeeper/serializers.py` with three functions. Callers pass optional kwargs for endpoint-specific overrides.

### Task 1: Create `serializers.py`

New file with:

- `serialize_memory(memory, *, truncate_content=None, exclude_fields=None)` — serializes `Memory` model, optional truncation + field exclusion
- `serialize_memory_link(link)` — serializes `MemoryLink` model
- `serialize_search_result(result, *, truncate_content=None, exclude_memory_fields=None, exclude_relevance_fields=None, round_relevance=None, include_links=True)` — composes the above, adding relevance scoring + links

**Preserves exact current output shape for MCP and dashboard.** `namespace` and `last_used` (on Memory) are intentionally absent from both old and new serializers — they're not exposed today. If needed later, they're added in one place.

**Files:** `src/lorekeeper/serializers.py` (new)

### Task 2: Refactor `handlers.py`

- Replace `from lorekeeper.services.search import SearchResult` → `from lorekeeper.serializers import serialize_search_result`
- Delete `_result_to_dict()` (~40 lines)
- Replace `[_result_to_dict(r) for r in results]` with `[serialize_search_result(r) for r in results]`

No behavior change — MCP output shape is identical.

### Task 3: Refactor `dashboard/app.py` `/api/search` endpoint

- Add `from lorekeeper.serializers import serialize_search_result`
- Replace inline dict loop (lines 304-322) with:
  ```python
  return [
      serialize_search_result(
          r,
          truncate_content=300,
          exclude_memory_fields={"created_at", "updated_at", "confidence", "confidence_count"},
          exclude_relevance_fields={"decay_factor"},
          round_relevance=4,
          include_links=False,
      )
      for r in results
  ]
  ```

Dashboard output shape preserved exactly: content truncated to 300, no `decay_factor`, no `links`, rounded scores to 4 decimal places, no `created_at`/`updated_at`/`confidence`/`confidence_count`.

---

## LKPR-44 — Config Override Validation

**Problem:** `server.py:init_service()` applies persisted config overrides via bare `setattr` with broad `except Exception`. Bad values (corrupted DB, stale overrides after schema changes) are silently swallowed with no error detail. No read-back verification.

**Solution:** Narrow exception types, add read-back verification, log specific error.

### Task 4: Update `server.py` `init_service()`

Current code (lines 36-42):

```python
for key, value in overrides.items():
    try:
        setattr(s, key, value)
    except Exception:
        log.warning("config_override_skipped", key=key, value=value)
```

Replace with:

```python
for key, value in overrides.items():
    try:
        setattr(s, key, value)
        getattr(s, key)  # confirm it reads back (catches silent failures)
    except (ValueError, TypeError, AttributeError) as e:
        log.warning("config_override_skipped", key=key, value=value, error=str(e))
```

Changes:

- `except Exception` → `except (ValueError, TypeError, AttributeError)` — catches only real type/attribute errors, not `KeyboardInterrupt` etc.
- `getattr(s, key)` read-back — confirms the value actually applies (catches Pydantic coercion failures where `setattr` succeeds but stores a wrong type)
- `error=str(e)` — logs the actual error message so operators can diagnose

---

## Full Commit Sequence

| #   | Commit                                                                                          | Files              |
| --- | ----------------------------------------------------------------------------------------------- | ------------------ |
| 1   | `[LKPR-43] feat: add shared serializers for Memory, MemoryLink, SearchResult`                   | `serializers.py`   |
| 2   | `[LKPR-43] refactor: replace inline _result_to_dict with shared serialize_search_result`        | `handlers.py`      |
| 3   | `[LKPR-43] refactor: dashboard search uses shared serializer with endpoint overrides`           | `dashboard/app.py` |
| 4   | `[LKPR-44] fix: validate config overrides at startup — narrow exceptions, read-back, log error` | `server.py`        |
| 5   | `[LKPR-0] chore: full test suite + lint pass`                                                   | —                  |

## Verification

```bash
# After each task
uv run pytest tests/ -v       # quick check for the changed test file
cd ~/.hermes/profiles/diana/projects/lorekeeper   # full suite before commit
uv run pytest -v              # 87/87 expected
uv run ruff check src tests   # clean
```

## Risk Mitigation

- **Serializers change is pure refactor** — same data flows through different code. All 87 tests exercise both paths (MCP handlers and dashboard have separate test coverage). If output shape changes, tests catch it via existing assertions.
- **Config override change is additive** — existing behavior preserved (skip + warn), just stricter on exception types and more verbose on logging. No code path changes for valid overrides.
- **Rollback:** `git checkout -- src/lorekeeper/serializers.py src/lorekeeper/handlers.py src/lorekeeper/dashboard/app.py src/lorekeeper/server.py` reverts all four files.
