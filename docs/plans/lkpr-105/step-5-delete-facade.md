# Step 5 — Delete the facade; server.py becomes the composition root

**Branch:** `chore/lkpr-105-step5-delete-facade`
**Depends on:** 4a, 4b, 4c, 4d all merged
**Files:** 2 deleted, ~4 modified — mostly deletions
**Behavior change:** none

## Precondition check (run before starting)

```
grep -rn "get_service\|MemoryService" src/lorekeeper/ --include='*.py' | grep -v services/
```

Expected: only `server.py` (init wiring) hits. If anything else appears, that
caller was missed in Step 4x — fix it there conceptually (tiny preamble
commit in this PR), don't grow this step.

## Changes

### 1. DELETE `src/lorekeeper/services/orchestrator.py` + `services/__init__.py`

### 2. `src/lorekeeper/server.py` — full composition root

`init_service()` wires bottom-up:

settings → engine (+probe) → `Database` + migrate → stores (Memory, Link,
Reflection, Metrics, Config, LinkSuggestion) → config overrides →
`KeywordIndex` → `ns_filter` → `MemoryCache(memories, kw, ns_filter)` →
`LinkCandidateGenerator` (moved from facade `__init__`) → domain services
(link → write → search → reflection → suggestion → import, explicit args) →
processors (memory, link, reflection, suggestion, admin) → BM25 bootstrap
`cache.rebuild_kw()` → encouragement rate → sweep scheduler (UNCHANGED — own
Database instance, assert in review).

Module singletons: the five processors + settings. Getters:
`get_memory_processor()`, `get_link_processor()`, `get_reflection_processor()`,
`get_suggestion_processor()`, `get_admin_processor()`, `get_settings()`.
DELETE `get_service()` and `get_suggestions_store()` (4d should have removed
last callers; the precondition grep proves it).

### 3. `tests/_helpers.py`

Delete `build_service()`. Add:

```python
@dataclass
class App:  # tests-only bundle — mirrors init_service() wiring 1:1
    stores: Stores
    cache: MemoryCache
    db: Database
    link_service: LinkService
    write_service: MemoryWriteService
    search_service: MemorySearchService
    reflection_service: ReflectionService
    suggestion_service: SuggestionService
    import_service: ImportService
    memory_processor: MemoryProcessor
    link_processor: LinkProcessor
    reflection_processor: ReflectionProcessor
    suggestion_processor: SuggestionProcessor
    admin_processor: AdminProcessor

def build_app(stores, engine, kw, settings) -> App: ...
```

Wiring order copied from `init_service()` — drift between the two is the #1
risk; add a comment in BOTH files pointing at each other. Provide a
backward-compat shim ONLY if the diff to update all fixtures in this PR is
unreasonable; prefer updating fixtures (setup-only changes).

### 4. `tests/test_sweep_lock_hold.py`

- `test_memory_service_has_no_db_parameter` / `test_memory_service_has_no_suggestions_attr`
  → replace with: `lorekeeper.services` module does not exist (importlib
  check), and the `init_service` AST check asserts SweepService gets its own
  `Database(...)` call (not the shared instance).

### 5. `tests/test_architecture.py`

Delete remaining `server → services.orchestrator` entry. **TEMPORARY_ALLOWED
must now be empty — delete the set and the exception mechanism.** Rule 5
flips to "lorekeeper.services must not exist" unconditionally.

## Verification

```
uv run pytest -q --ignore=tests/e2e
uv run pytest tests/test_architecture.py tests/test_sweep_lock_hold.py -v
uv run ruff check src tests scripts/ && uv run mypy src
test ! -d src/lorekeeper/services && echo GONE
grep -rn "MemoryService" src/ tests/ --include='*.py'   # → empty (or only in relocated-test comments)
uv run python -c "from lorekeeper.server import init_service"   # imports clean
```

E2E: run `uv run pytest tests/e2e/ -m e2e` locally — this step touches server
wiring, unit CI won't catch app-startup breakage.

## AC

- [ ] `services/` gone; `get_service` gone; processor getters only
- [ ] `TEMPORARY_ALLOWED` deleted — architecture test enforces final rules bare
- [ ] `build_app()` mirrors `init_service()` with cross-reference comments
- [ ] Sweep isolation still asserted; E2E run locally and green
