# LKPR-50 — Dashboard tests, serialization unification, engine ABC cleanup, quality gate

**Status:** Proposal — not yet implemented
**Filed:** 2026-05-31 by Diana

## Scope

Grouped code-hygiene work across the dashboard, backend, and CI. Tests first, then cleanups.

## Per-Step Detail

### Step 1 — Tests (foundation)

Create `tests/test_dashboard.py` using FastAPI's `TestClient` to exercise every route:

- `GET /api/memories` — list with/without deleted
- `GET /api/memories/{id}` — found, 404
- `PATCH /api/memories/{id}` — update fields
- `DELETE /api/memories/{id}` — delete, 404
- `GET /api/links` — list with/without deleted
- `POST /api/links` — create, 404 on missing source/target
- `DELETE /api/links/{id}` — delete, 404
- `POST /api/search` — search with query
- `GET /api/config` — read config with overridden_keys
- `PATCH /api/config` — update config
- `GET /api/export` — export dump
- `POST /api/import/preview` — import preview from file
- `POST /api/import/confirm` — import confirm
- `GET /api/sessions` — list with/without content
- `GET /api/sessions/{id}` — 404
- `GET /api/reflections` — list
- `GET /api/reflections/{id}` — 404
- `GET /api/metrics` — get metrics

Extend `tests/test_handlers.py` with error-path tests for `server.py`:

- `lore_insert` with no memories (should succeed with empty result)
- `lore_insert` with invalid inline link format (string not list)
- `lore_search` with `refine_from` > cap (200)

Add `tests/test_serializers.py`:

- `serialize_memory` — basic, with truncation, with field exclusion
- `serialize_memory_link` — stable shape
- `serialize_search_result` — basic, with exclude/round/links toggle

**New files:** `tests/test_dashboard.py`, `tests/test_serializers.py`
**Modified files:** `tests/test_handlers.py`

### Step 2 — Dashboard serialization unification

In `dashboard/app.py`:

- Replace `dict(row)` in `list_memories()` with a helper that preserves `link_count` augmentation but uses the shared serialization path
- Replace `dict(row)` in `get_memory()` and `dict(row)` in `update_memory()`
- Replace `lnk.model_dump()` with `serialize_memory_link()` in `get_memory()`, `list_all_links()`, `create_link()`
- Replace `dict(r)` with the serializer in `list_reflections()`, `get_reflection_detail()`, `list_sessions()`, `get_session_detail()`

In `api.js`:

- Remove `window.showToast = showToast` (line 25)
- Remove `window.api = api` (line 26)
- Verify no other module references `window.api` or `window.showToast` (all should use imports from LKPR-45's tab-registry)

**Modified files:** `src/lorekeeper/dashboard/app.py`, `src/lorekeeper/dashboard/static/js/api.js`

### Step 3 — Config override type validation

In `dashboard/app.py` `update_config()`:

- Instead of blanket `setattr(s, key, value)`, type-check the value before applying
- Build a type map from the ConfigUpdate model annotations: `{field_name: field_type}`
- For each override, validate `isinstance(value, expected_type)` — int for int fields, float for float, bool for bool
- On mismatch, return 422 with `{"detail": f"Config '{key}' expects {expected_type.__name__}, got {type(value).__name__}"}`
- Keep the `_READONLY_KEYS` guard intact (blocks `data_dir`, `embedding_model`)

**Modified files:** `src/lorekeeper/dashboard/app.py`

### Step 4 — MemoryEngine ABC cleanup

In `memory_engine.py`:

- Add `find_mem0_id(lore_id: str) -> str | None` to the ABC — orchestrator's `_auto_link` path needs this (currently FakeEngine-only)
- Remove `delete_by_mem0_id` if orchestrator never calls it (grep to confirm)
- Add docstring to `normalize_score` clarifying that each engine handles this internally but the method exists for direct callers

In `lancedb_engine.py`:

- Implement `find_mem0_id` (iterate `get_all()`, return first match)

In `chromadb_engine.py`:

- Implement `find_mem0_id` (iterate `get_all()`)
- Fix `normalize_score` being unused — audit if caller actually calls it on the ABC path

In `tests/test_orchestrator.py` (FakeEngine):

- Ensure `FakeEngine` matches the updated ABC (remove/bridge methods as needed)

**Modified files:**

- `src/lorekeeper/services/memory_engine.py`
- `src/lorekeeper/services/lancedb_engine.py`
- `src/lorekeeper/services/chromadb_engine.py`
- `tests/test_orchestrator.py`

### Step 5 — mypy in pre-commit (non-blocking advisory)

In `.githooks/pre-commit`:

- Add `uv run mypy src` after ruff check, but wrap it so failures don't block the commit:
  ```bash
  echo "Running mypy (advisory — failures don't block)..."
  uv run mypy src || echo "⚠️  mypy found issues — review before push"
  ```

In `pyproject.toml`:

- Relax specific `# type: ignore` exemptions that are known, add `warn_unused_ignores = true` to surface stale `type: ignore` comments

Fix existing `# type: ignore[union-attr]` in `orchestrator.py` `_row_to_memory` — the `row.keys()` pattern can be replaced with a cleaner guard.

**Modified files:** `.githooks/pre-commit`, `pyproject.toml`, `src/lorekeeper/services/orchestrator.py`

## Migration

No schema changes — this is pure code hygiene.

## Risk Items

- **Test reliability (Step 1):** Dashboard tests use `TestClient` with an isolated in-memory SQLite DB. Must use `tmp_path` fixture — don't touch the real `~/.lorekeeper/`.
- **Serialization unification (Step 2):** The `link_count` augmentation in `list_memories()` happens after serialization — must preserve or add as optional field to `serialize_memory`.
- **Config validation (Step 3):** `isinstance(1, float)` is `False` in Python (int is not float). Use `isinstance(value, (int, float))` for float fields, or coerce int→float.
- **ABC cleanup (Step 4):** Grep for every `delete_by_mem0_id` and `normalize_score` call site to confirm which are actually used before removing.

## Verification

Each step has its own verification:

1. `uv run pytest -v tests/test_dashboard.py tests/test_serializers.py` — all pass
2. `uv run pytest -v` — full suite green; launch dashboard and verify memories/links tabs load
3. `PATCH /api/config` with `{"w_semantic": "banana"}` returns 422
4. `FakeEngine` has `find_mem0_id` method; all existing tests pass
5. Pre-commit hook runs `mypy src` without blocking; `_row_to_memory` has no `type: ignore`
