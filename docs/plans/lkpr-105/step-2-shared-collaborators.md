# Step 2 — Shared collaborators: MemoryCache, Database.commit, safe metrics

**Branch:** `chore/lkpr-105-step2-shared-collaborators`
**Files:** 1 new, 3 modified, 1 new test file
**Behavior change:** none — facade methods become one-line delegations

## Changes

### 1. NEW `src/lorekeeper/domains/memory/cache.py` — `MemoryCache`

Move the bodies of `MemoryService._all_memories`, `_invalidate_cache`,
`_rebuild_kw` (orchestrator.py lines 117-142) verbatim:

```python
class MemoryCache:
    """LKPR-60 in-process cache of all Memory rows + BM25 rebuild coupling.

    Cache always holds the full (include_deleted=True) dataset;
    include_deleted=False is filtered in Python. None = dirty.
    MUST be a single shared instance across all services — two instances
    silently split invalidation.
    """
    def __init__(self, memories: MemoryStore, kw: KeywordIndex,
                 ns_filter: list[str] | None) -> None: ...
    def all_memories(self, include_deleted: bool = False) -> dict[str, Memory]: ...
    def invalidate(self) -> None: ...
    def rebuild_kw(self) -> None: ...  # invalidate + reload(include_deleted=True) + kw.rebuild
```

Import direction: domains/memory → domains.memory.repository + infra — legal,
no exception entries needed.

### 2. `src/lorekeeper/infra/database.py` — add `commit()`

```python
def commit(self) -> None:
    """Flush pending writes. Commit control belongs to the calling service."""
    self.conn.commit()
```

### 3. `src/lorekeeper/platform/metrics/repository.py` — `increment_metric_safe()`

Move facade `_increment_metric` body (orchestrator.py lines 146-154):
try increment + `self._conn.commit()`, swallow `sqlite3.Error` at WARNING
(`metric_increment_failed`, exc_info=True). Docstring documents the exception
to the no-inline-commit rule: fire-and-forget is the metric contract.

### 4. `src/lorekeeper/services/orchestrator.py` — delegate

- `__init__`: build `self._cache = MemoryCache(memories, keyword_index, self._ns_filter)`
- `_all_memories` → `return self._cache.all_memories(include_deleted)`
- `_invalidate_cache` → `self._cache.invalidate()`
- `_rebuild_kw` → `self._cache.rebuild_kw()`
- `_increment_metric` → `self.metrics.increment_metric_safe(tool_name)`
- `commit` → `self._conn.commit()` stays (facade dies in Step 5)

Public surface unchanged — zero caller changes, zero test changes expected
(if `tests/test_memory_service.py` pokes `svc._memory_cache` directly, adjust
those asserts to `svc._cache._memory_cache` in this PR and note it; full
relocation happens in Step 6).

### 5. NEW `tests/domains/memory/test_cache.py` (+ `tests/domains/__init__.py`, `tests/domains/memory/__init__.py`)

New tests written directly against `MemoryCache` (constructed with real
MemoryStore + KeywordIndex on tmp_path):

- cache starts dirty (None)
- `all_memories()` populates; second call hits cache (no re-query — assert via
  row-count probe or monkeypatched store method)
- `invalidate()` marks dirty; next call reloads
- `rebuild_kw()` invalidates + rebuilds BM25 (search_normalized returns hits)
- `include_deleted=False` filters soft-deleted, `True` returns all

Note: the 5 look-alike tests in `tests/test_memory_service.py` stay where they
are until Step 6 (they exercise the facade path; keeping both until cutover is
intentional double-coverage, deleted in Step 6).

## Verification

```
uv run pytest tests/domains/memory/test_cache.py -v
uv run pytest -q --ignore=tests/e2e
uv run pytest tests/test_architecture.py -v      # no new edges
uv run ruff check src tests scripts/ && uv run mypy src
```

## AC

- [ ] Facade `_all_memories`/`_invalidate_cache`/`_rebuild_kw`/`_increment_metric` are one-line delegations
- [ ] `MemoryCache` has direct unit tests
- [ ] No caller outside the facade changed
- [ ] No new architecture exception entries
