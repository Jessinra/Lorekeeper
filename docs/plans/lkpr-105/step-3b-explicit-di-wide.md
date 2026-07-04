# Step 3b — Explicit DI: wide services (Search, Write, Suggestion)

**Branch:** `chore/lkpr-105-step3b-di-wide`
**Files:** 2 service files + orchestrator.py `__init__` + `tests/test_architecture.py` (delete 2 entries)
**Behavior change:** none

## Changes

### 1. `domains/memory/service.py` — both classes

Grep-verified deps (recount at implementation; drop unused, add missing):

```python
class MemorySearchService:
    # body uses: _engine, _kw, memories, links, _all_memories(cache),
    # settings, _conn(db: usage-count bump), _ns_filter, _increment_metric
    def __init__(self, engine, kw, memories, links, cache, metrics,
                 settings, db, ns_filter) -> None: ...

class MemoryWriteService:
    # body uses: _engine, memories, links, cache(_invalidate/_rebuild_kw),
    # metrics, settings, db(_conn), namespace(_namespace), ns_filter,
    # link_service, _extract_title
    def __init__(self, engine, memories, links, cache, metrics, settings,
                 db, namespace, ns_filter, link_service) -> None: ...
```

- `svc._extract_title(...)` in write service → free `extract_title(...)`
  (same module — trivial). Tests monkey-patching `svc._extract_title` must
  patch `lorekeeper.domains.memory.service.extract_title` — fix in this PR.
- `svc._all_memories(...)` → `self._cache.all_memories(...)`,
  `svc._rebuild_kw()` → `self._cache.rebuild_kw()`, etc.
- `svc._conn.commit()` → `self._db.commit()`.
- Width is intentional (9-10 params) — documents real coupling; do NOT
  introduce a bundle to shorten it.

### 2. `domains/suggestion/service.py`

Grep-verified deps: `memories(2), links(2), settings, _ns_filter,
_link_candidate_generator, _kw, _increment_metric, _engine, _conn` + the
`svc.memories._db.transaction()` reach-in:

```python
def __init__(self, candidate_generator, engine, kw, memories, links,
             metrics, settings, db, ns_filter) -> None: ...
```

`svc.memories._db.transaction()` → `self._db.transaction()` — kills the last
private reach-in.

### 3. `services/orchestrator.py` `__init__`

Full construction order: `LinkService(links)` →
`MemoryWriteService(engine, memories, links, cache, metrics, s, db, namespace, ns_filter, link_service)`
→ `MemorySearchService(...)` → `ReflectionService(...)` (from 3a, now real
write_service) → `SuggestionService(link_candidate_generator, ...)` →
`ImportService(...)`.

The facade's `_link_candidate_generator` construction stays in facade
`__init__` (moves to server.py in Step 5).

### 4. Facade shims now dead

After this step no domain service calls back into the facade. The facade's
`_extract_title` staticmethod, `_all_memories`, `_rebuild_kw`,
`_invalidate_cache`, `_increment_metric` remain only for external callers
(tests poke some of them) — leave them; they die in Step 5/6.

### 5. `tests/test_architecture.py`

Delete the 2 remaining domain→orchestrator entries (memory.service,
suggestion.service). After this PR: **zero domain→services edges**; grep
`services.orchestrator` in `src/lorekeeper/domains/` is empty.

## Verification

```
uv run pytest -q --ignore=tests/e2e
uv run pytest tests/test_architecture.py -v
uv run ruff check src tests scripts/ && uv run mypy src
grep -rn "MemoryService\|services.orchestrator" src/lorekeeper/domains/   # → empty
grep -rn "_db\.\|_conn\." src/lorekeeper/domains/*/service.py src/lorekeeper/domains/memory/import_service.py | grep -v "self\._db\b"   # no foreign privates
```

## AC

- [ ] Zero `svc.` references, zero `MemoryService` imports in `domains/`
- [ ] `SuggestionService` transaction via own `db` dep — no `.memories._db`
- [ ] Monkey-patch call sites migrated to module-level `extract_title`
- [ ] 2 exception entries deleted; domain ring fully clean
