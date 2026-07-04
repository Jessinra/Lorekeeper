# Step 4d — AdminProcessor: metrics, config, sweep control

**Branch:** `chore/lkpr-105-step4d-admin-processor`
**Depends on:** Step 2 (stores + Database.commit only)
**Files:** 1 new, 4 modified
**Behavior change:** none

## Changes

### 1. NEW `src/lorekeeper/processors/admin.py` — `AdminProcessor`

Cross-cutting operational use cases that don't belong to a domain slice:

```python
class AdminProcessor:
    def __init__(self, config: ConfigStore, metrics: MetricsStore,
                 suggestions: LinkSuggestionStore, settings: Settings,
                 db: Database) -> None: ...

    def get_metrics(self, ...) -> ...          # from routes/metrics.py
    def get_config(self) -> dict:              # settings + overridden_keys
    def set_config(self, key, value) -> ...    # validation + set_override + commit
    def trigger_sweep(self) -> None:
        # set_override("sweep_next_run_at", now) + commit — kills the
        # svc.config.set_override reach-through in routes/suggestions.py
    def sweep_status(self) -> dict:            # overrides + newest-suggestion fallback
```

### 2. `dashboard/routes/metrics.py`, `config.py`

Delegate to `get_admin_processor()`. config.py keeps Pydantic request models
and HTTP mapping; validation of key/value moves into `set_config`.

### 3. `dashboard/routes/suggestions.py`

`trigger_sweep` / `sweep_status` → AdminProcessor. After this, suggestions.py
imports NO store/config directly (pending list/count go via
SuggestionProcessor from 4a — add `count_pending(memory_id)` /
`list_pending(...)` thin methods there if 4a didn't already cover the GET
routes; keep that addition inside this PR).

### 4. `server.py`

Construct + getter. After 4a–4d: no dashboard route imports
`get_service`/`get_suggestions_store` — both getters should now have zero
route callers; delete `get_suggestions_store()` if the last caller is gone
(check MCP handlers too).

### 5. Tests

NEW `tests/processors/test_admin_processor.py` — config set/get round-trip,
trigger_sweep writes override + commits, sweep_status fallback logic.
`tests/test_dashboard.py` fixtures updated (setup only).

## Verification

```
uv run pytest -q --ignore=tests/e2e
uv run pytest tests/test_architecture.py -v
uv run ruff check src tests scripts/ && uv run mypy src
grep -rn "get_service\|get_suggestions_store" src/lorekeeper/dashboard/routes/   # → empty
grep -rn "commit()" src/lorekeeper/dashboard/ src/lorekeeper/api/               # → empty
```

## AC

- [ ] Zero `get_service`/store getters/`commit()` in dashboard routes
- [ ] All remaining presentation exception entries for dashboard deleted
- [ ] Only `server.py`'s own facade usage remains in TEMPORARY_ALLOWED
