# Step 3a — Explicit DI: narrow services (LinkService, ImportService, ReflectionService)

**Branch:** `chore/lkpr-105-step3a-di-narrow`
**Files:** 3 service files + orchestrator.py `__init__` + `tests/test_architecture.py` (delete 3 entries)
**Behavior change:** none

## Pattern (applies to all three)

Replace `def __init__(self, svc: MemoryService)` with explicit deps. Drop the
`TYPE_CHECKING` import of `MemoryService`. Every `svc.X` body reference
becomes `self._X`. The facade constructs the service with explicit args —
callers of the facade unchanged.

Metric increments: replace `svc._increment_metric(...)` with
`self._metrics.increment_metric_safe(...)` where the service currently does
it — metrics moves fully OUT of domain services in Step 4x when processors
take over; in this step keep call positions identical (pass `metrics` as a
dep where used). Zero behavior change trumps purity here.

## Changes

### 1. `domains/link/service.py`

Body uses only `svc.links` (verified by grep):

```python
def __init__(self, links: LinkStore) -> None:
    self._links = links
```

Facade: `self.link_service = LinkService(links)`.
(`validate_relation_type` is already a staticmethod — untouched.)

### 2. `domains/memory/import_service.py`

Grep-verified deps: `memories(2), links(2), _conn(2), _rebuild_kw(1), _namespace(1), _engine(1)`:

```python
def __init__(self, engine: LanceDBEngine, memories: MemoryStore,
             links: LinkStore, cache: MemoryCache, db: Database,
             namespace: str) -> None: ...
```

`svc._conn.commit()` → `self._db.commit()`; `svc._rebuild_kw()` →
`self._cache.rebuild_kw()`.

### 3. `domains/reflection/service.py`

Grep-verified deps: `reflections(4), _increment_metric(2), _conn(2),
memory_write_service(1), _rebuild_kw(1), _extract_title(1)`:

```python
def __init__(self, reflections: ReflectionStore, metrics: MetricsStore,
             db: Database, cache: MemoryCache,
             write_service: MemoryWriteService) -> None: ...
```

`svc._extract_title(...)` → module-level `extract_title(...)` (import the
free function from `domains.memory.service`). CHECK first: if any test
monkey-patches `_extract_title` on the reflection path, patch target becomes
`lorekeeper.domains.memory.service.extract_title` — fix those tests in this
PR (setup-only change).

### 4. `services/orchestrator.py` `__init__`

Construction order matters: `LinkService` → `MemoryWriteService` (still takes
`self` until 3b) → `ImportService(engine, memories, links, self._cache, db, namespace)`
→ `ReflectionService(reflections, metrics, db, self._cache, self.memory_write_service)`.

NOTE: facade needs a `Database` handle — it currently only has
`memories._conn`. Thread `db: Database` into `MemoryService.__init__` as a
new param (server.py + `tests/_helpers.build_service` updated — 2 call
sites). CHECK `test_sweep_lock_hold.test_memory_service_has_no_db_parameter`:
it asserts the facade takes no `db` param! Options: (a) pass `db` and update
that test's invariant to "no db param on DOMAIN services' shared state" — but
simplest honest fix: the test guards against the sweep sharing the main DB
connection; passing the main `Database` for commit control doesn't violate
the sweep isolation it protects. Update the test with a comment explaining
the new invariant (sweep still constructs its OWN Database — assert that
instead). Flag this in the PR description.

### 5. `tests/test_architecture.py`

Delete the 3 domain→orchestrator entries for link/import/reflection.

## Verification

```
uv run pytest -q --ignore=tests/e2e
uv run pytest tests/test_architecture.py tests/test_sweep_lock_hold.py -v
uv run ruff check src tests scripts/ && uv run mypy src
grep -n "MemoryService" src/lorekeeper/domains/link/service.py src/lorekeeper/domains/reflection/service.py src/lorekeeper/domains/memory/import_service.py   # → empty
```

## AC

- [ ] Three services have zero `svc.` references and no `MemoryService` import
- [ ] Facade constructs them with explicit args; public surface unchanged
- [ ] `test_sweep_lock_hold` invariant updated with rationale, sweep isolation still asserted
- [ ] 3 exception entries deleted
