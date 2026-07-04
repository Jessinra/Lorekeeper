# Step 2 — Shared collaborators: MemoryCache, Database.commit, safe metrics

**Branch:** `chore/lkpr-105-step2-shared-collaborators`
**Depends on:** Step 0 merged
**Files:** 2 new (cache.py + test + 2 package init files), 3 modified (database, metrics, orchestrator)
**Behavior change:** none — facade methods become one-line delegations

## Changes

### 1. NEW `src/lorekeeper/domains/memory/cache.py` — `MemoryCache`

Move the bodies of `_all_memories`, `_invalidate_cache`, `_rebuild_kw` from orchestrator.py into a standalone class:

- `__init__(self, memories: MemoryStore, kw: KeywordIndex, ns_filter: list[str] | None)`
- `all_memories(self, include_deleted: bool = False) -> dict[str, Memory]`
- `invalidate(self) -> None`
- `rebuild_kw(self) -> None`

Import direction: `domains/memory` → `domains.memory.repository` (valid same-package) + `infra.keyword_index` (valid lower-layer).

### 2. `src/lorekeeper/infra/database.py` — add `commit()`

```python
def commit(self) -> None:
    """Flush pending writes. Commit control belongs to the calling service."""
    self._conn.commit()
```

### 3. `src/lorekeeper/platform/metrics/repository.py` — add `increment_metric_safe()`

Move facade `_increment_metric` body: try `increment_metric` + `self._conn.commit()`, swallow `sqlite3.Error` at WARNING. Documents exception to the no-inline-commit rule.

### 4. `src/lorekeeper/services/orchestrator.py` — delegate

- `__init__`: build `self._cache = MemoryCache(self.memories, self._kw, self._ns_filter)`
- Remove `self._memory_cache` raw dict attribute
- `_all_memories` → `return self._cache.all_memories(include_deleted)`
- `_invalidate_cache` → `self._cache.invalidate()`
- `_rebuild_kw` → `self._cache.rebuild_kw()`
- `_increment_metric` → `self.metrics.increment_metric_safe(tool_name)`
- `commit` → `self._conn.commit()` stays (facade dies in Step 5)

### 5. NEW `tests/domains/__init__.py`, `tests/domains/memory/__init__.py`

Empty package init files for test directory hierarchy.

### 6. NEW `tests/domains/memory/test_cache.py`

Direct MemoryCache tests:

- cache starts dirty (all_memories first call populates)
- second call hits cache (no re-query)
- invalidate() marks dirty; next call reloads
- rebuild_kw() invalidates + rebuilds BM25
- include_deleted=False filters soft-deleted

## Verification

```bash
uv run pytest tests/domains/memory/test_cache.py -v
uv run pytest -q --ignore=tests/e2e
uv run pytest tests/test_architecture.py -v
uv run ruff check src tests scripts/ && uv run mypy src
```

## AC

- [ ] `_all_memories`/`_invalidate_cache`/`_rebuild_kw`/`_increment_metric` are one-line delegations in facade
- [ ] `MemoryCache` has direct unit tests
- [ ] `Database.commit()` added as public method
- [ ] `MetricsStore.increment_metric_safe()` added
- [ ] No callers outside the facade changed
- [ ] No new architecture exception entries
