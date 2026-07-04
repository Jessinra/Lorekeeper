# Step 4c — ReflectionProcessor + LinkProcessor

**Branch:** `chore/lkpr-105-step4c-reflection-link-processors`
**Depends on:** Step 3b
**Files:** 2 new, 4 modified
**Behavior change:** none

## Changes

### 1. NEW `src/lorekeeper/processors/reflection.py` — `ReflectionProcessor`

```python
class ReflectionProcessor:
    def __init__(self, reflection_service, metrics, db) -> None: ...
    def submit_reflection(self, **kwargs) -> dict:
        # input guards from server.py lore_reflect tool body (session_id/
        # summary required etc. — move whatever validation lives in the tool
        # body today; metric increment moves here from ReflectionService)
    def processed_session_ids(self) -> list[str]: ...
```

### 2. NEW `src/lorekeeper/processors/link.py` — `LinkProcessor`

Orchestration currently inline in `dashboard/routes/links.py` (list, create
with existence validation, delete) moves here:

```python
class LinkProcessor:
    def __init__(self, link_service, memories: MemoryStore,
                 links: LinkStore, metrics, db) -> None: ...
    def list_links(self, ...) -> ...
    def create_link(self, source_id, target_id, relation_type, reason) -> MemoryLink:
        # target/source existence check (404 signalling via LookupError —
        # route maps to HTTPException), relation validation via
        # LinkService.validate_relation_type, insert, commit
    def delete_link(self, link_id) -> None: ...
```

Read routes that are literally one store call MAY stay as store reads until
Step 5's final sweep — but the write paths (create/delete + commit) MUST move
now (commit out of presentation).

### 3. `server.py`

Construct both processors + getters; rewire `lore_reflect` and
`lore_processed_sessions` tool bodies.

### 4. `dashboard/routes/reflections.py`, `dashboard/routes/links.py`

reflections.py: reads via `ReflectionProcessor` (add thin read methods
delegating to store — uniformity over cleverness). links.py: all writes via
`LinkProcessor`; no `commit()` remains in the route.

### 5. Tests

- NEW `tests/processors/test_reflection_processor.py` /
  `test_link_processor.py` — move the validation-focused tests from
  test_handlers.py / test_dashboard.py where they exist; add create_link
  404-signal test.

## Verification

```
uv run pytest -q --ignore=tests/e2e
uv run pytest tests/test_architecture.py -v
uv run ruff check src tests scripts/ && uv run mypy src
grep -n "commit()" src/lorekeeper/dashboard/routes/links.py src/lorekeeper/dashboard/routes/reflections.py   # → empty
```

## AC

- [ ] Reflection + link write orchestration in processors; routes are shims
- [ ] No commit() in these routes
- [ ] Related exception entries deleted
