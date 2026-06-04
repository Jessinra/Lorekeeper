---
id: LKPR-51
title: LinkStore decomposition — split god object into focused data stores
type: enhancement
sprint: ~
rice_score: ~
filed_by: Diana
filed_date: 2026-05-31
---

# [LKPR-51] LinkStore decomposition — split god object into focused data stores

## Problem

`LinkStore` in `services/link_store.py` is a 637-line god object that owns **six distinct domains** through a single SQLite connection:

| Domain | Methods | Lines |
|---|---|---|
| Memory rows | `upsert_memory_row`, `get_memory_row`, `get_memory_row_by_title`, `all_memory_rows`, `update_memory_fields`, `delete_memory_row` | ~100 |
| Links | `insert_link`, `links_for_memory`, `get_link`, `update_link_fields`, `all_links`, `delete_link` | ~40 |
| Reflections | `insert_reflection`, `get_reflection`, `all_reflections` | ~35 |
| Sessions | `upsert_session`, `upsert_sessions_bulk`, `all_processed_session_ids`, `all_sessions`, `sessions_with_content`, `get_session`, `sessions_for_reflection` | ~80 |
| API Metrics | `increment_metric`, `get_metrics` | ~50 |
| Config overrides | `get_config_overrides`, `set_config_override`, `delete_config_override` | ~25 |
| Schema + migrations | `SCHEMA`, `_migrate`, `_migrate_*` (6 migrations) | ~100 |
| Helpers | `__init__`, `close`, `_row_to_link` | ~20 |

**Impact:**
- **Every new feature** adds methods to this file. The gravity well makes it the default place to put things, even when they don't belong together.
- **`orchestrator.py`** (730 lines) accesses `self._store` for ALL domains — memories, links, reflections, sessions, metrics. The orchestrator knows about the SQLite schema because the store exposes raw `sqlite3.Row` objects instead of typed models.
- **`dashboard/app.py`** accesses `get_service()._store` directly through a private attribute (17 call sites) for memory/links/sessions/reflections/metrics/config data access, plus 2 `get_service()._settings` accesses for settings data — **19 private attribute accesses** total, bypassing both the orchestrator and the type system.
- **Migrations are ad-hoc** — run at every `__init__`, unversioned, destructive (deletes rows), and can't be rolled back. Adding a new migration requires adding another `_migrate_*` method and calling it in the chain.

## Solution

Extract focused data store classes, each owning its domain. Keep a shared `Database` class for the SQLite connection lifecycle.

### New structure

```
services/
├── database.py         # Shared SQLite connection, WAL mode, FKs, versioned migrations
├── memory_store.py     # Memory row CRUD (extracted from LinkStore)
├── link_store.py       # Link CRUD (stays, but loses non-link responsibilities)
├── reflection_store.py # Reflection + Session CRUD (they share FKs)
├── metrics_store.py    # API metrics (minimal, no dependencies)
└── config_store.py     # Config overrides (minimal, no dependencies)
```

### Why this grouping

- **Reflection + Session together**: They share a FK (`sessions.reflection_id → reflections.id`), and session content columns were added alongside reflections. Keeping them in one store preserves transactional consistency without cross-store coordination.
- **Metrics separate**: Zero FK dependencies, uses its own table. Simple standalone.
- **Config overrides separate**: Uses its own table, JSON-serialized values. Standalone.
- **LinkStore stays but trimmed**: It still manages link CRUD + the link-memory FK relationship. Lose memory rows, reflections, sessions, metrics, and config.

### Database class

Centralizes:
- SQLite connection creation (WAL mode, FKs, `row_factory = sqlite3.Row`)
- `close()` — single method to tear down all connections
- Versioned migrations via a `_schema_version` table and numbered migration functions
- Ad-hoc `_migrate_*` methods removed from individual stores

```python
class Database:
    def __init__(self, db_path: Path): ...
    def migrate(self): ...  # applies pending migrations by version number
    def execute(self, sql, params=None): ...
    def commit(self): ...
    def close(self): ...
```

### Per-store interface

**`MemoryStore`:**
```python
class MemoryStore:
    def __init__(self, db: Database): ...
    def upsert_memory_row(self, id, title, description, content, ...): ...
    def get_memory_row(self, id, namespaces=None) -> Memory | None: ...
    def get_memory_row_by_title(self, title, namespaces=None) -> Memory | None: ...
    def all_memory_rows(self, include_deleted=False, namespaces=None) -> list[Memory]: ...
    def update_memory_fields(self, id, **fields): ...
    def delete_memory_row(self, id): ...
```
Returns `Memory` model instances (typed), not raw `sqlite3.Row`.

**`LinkStore` (trimmed):**
```python
class LinkStore:
    def __init__(self, db: Database): ...
    def insert_link(self, ...) -> MemoryLink: ...
    def links_for_memory(self, memory_id) -> list[MemoryLink]: ...
    def get_link(self, link_id) -> MemoryLink | None: ...
    def update_link_fields(self, link_id, **fields): ...
    def all_links(self) -> list[MemoryLink]: ...
    def delete_link(self, link_id): ...
```

**`ReflectionStore` (includes sessions):**
```python
class ReflectionStore:
    def __init__(self, db: Database): ...
    def insert_reflection(self, ...): ...
    def get_reflection(self, id) -> Reflection | None: ...
    def all_reflections(self) -> list[Reflection]: ...
    def upsert_session(self, ...): ...
    def upsert_sessions_bulk(self, rows): ...
    def get_session(self, id) -> SessionRecord | None: ...
    def all_sessions(self) -> list[SessionRecord]: ...
    def sessions_with_content(self) -> list[SessionRecord]: ...
    def sessions_for_reflection(self, reflection_id) -> list[SessionRecord]: ...
    def all_processed_session_ids(self) -> set[str]: ...
```

**`MetricsStore`:**
```python
class MetricsStore:
    def __init__(self, db: Database): ...
    def increment_metric(self, tool_name): ...
    def get_metrics(self, hours=24) -> list[dict]: ...
```

**`ConfigStore`:**
```python
class ConfigStore:
    def __init__(self, db: Database): ...
    def get_overrides(self) -> dict: ...
    def set_override(self, key, value): ...
    def delete_override(self, key): ...
```

### Orchestrator wiring

`MemoryService.__init__` receives the focused stores instead of one `LinkStore`:

```python
class MemoryService:
    def __init__(
        self,
        engine: MemoryEngine,
        memories: MemoryStore,
        links: LinkStore,
        reflections: ReflectionStore,
        metrics: MetricsStore,
        config: ConfigStore,
        keyword_index: KeywordIndex,
        settings: Settings,
    ):
```

### Dashboard wiring

`server.py` `init_service()` instantiates the `Database` + all stores, passes them to `MemoryService`. Dashboard `app.py` accesses individual stores via `get_service().memories`, `get_service().links`, etc. instead of `get_service()._store` — no private attribute access needed.

```python
db = Database(s.sqlite_path)
db.migrate()  # run versioned migrations once at startup
memories = MemoryStore(db)
links = LinkStore(db)
reflections = ReflectionStore(db)
metrics = MetricsStore(db)
config = ConfigStore(db)
svc = MemoryService(engine, memories, links, reflections, metrics, config, kw, s)
```

### Versioned migrations

Replace the current `_migrate()` chain with a `_schema_version` table and numbered migration functions:

```sql
CREATE TABLE IF NOT EXISTS _schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Migration functions are named `migrate_001_add_last_used_column()`, `migrate_002_add_namespace_column()`, etc. The `Database.migrate()` method discovers pending migrations by comparing the current version against a `MIGRATIONS` ordered list, applying each in sequence within a transaction.

## Acceptance Criteria

- [ ] All existing LinkStore functionality is preserved: memory CRUD, link CRUD, reflection/session CRUD, metrics, config overrides
- [ ] `Database` class owns connection lifecycle + versioned migrations; ad-hoc `_migrate_*` methods removed
- [ ] `MemoryService.__init__` accepts focused stores instead of one `LinkStore`; orchestrator uses typed stores
- [ ] Dashboard accesses stores via named attributes (`get_service().memories`) not `_store`
- [ ] All stores return dict-shaped rows (compatible with current `sqlite3.Row` callers); typed Pydantic model conversion deferred to a follow-up ticket
- [ ] All 121+ existing tests pass with minimal fixture changes (test helper pattern that instantiates stores from a shared `Database`)
- [ ] `LinkStore` file drops from 637 to ~150 lines (link-only + `_row_to_link`)

## Affected Files

### Backend — new
- `src/lorekeeper/services/database.py` — `Database` class with versioned migration runner
- `src/lorekeeper/services/memory_store.py` — extracted from `LinkStore`
- `src/lorekeeper/services/reflection_store.py` — extracted from `LinkStore`
- `src/lorekeeper/services/metrics_store.py` — extracted from `LinkStore`
- `src/lorekeeper/services/config_store.py` — extracted from `LinkStore`

### Backend — modified
- `src/lorekeeper/services/link_store.py` — trimmed to link-only CRUD + `_row_to_link`
- `src/lorekeeper/services/orchestrator.py` — accept focused stores, update `self._store.*` references
- `src/lorekeeper/server.py` — instantiate `Database` + stores, pass to `MemoryService`
- `src/lorekeeper/__init__.py` — re-export if needed

### Dashboard
- `src/lorekeeper/dashboard/app.py` — access stores via typed attributes, not `get_service()._store`

### Tests
- `tests/test_link_store.py` — refactor fixtures, adapt to new store interfaces
- `tests/test_orchestrator.py` — update fixture to pass focused stores
- `tests/test_dashboard.py` (from LKPR-50) — already uses `TestClient`, will validate the new wiring

## Dependencies

- **LKPR-50**: Dashboard + MCP tests must be merged first (provides the regression net). The decomposition changes store interfaces, and `test_dashboard.py` from LKPR-50 catches wiring regressions.

## Required Updates

- **CLAUDE.md**: [ ] Update Architecture section to reflect decomposed stores
- **README.md**: [ ] N/A (no user-facing change)
- **Skills**: [ ] Update `lorekeeper-dev` skill with new architecture + migration system
- **Backlog**: [ ] N/A

## Open Questions

- _`MemoryStore` return type resolved: dict-shaped for now, typed models deferred_ (see AC #5 — the decomposition diff is already big enough without changing the type contract)
- How to handle the `close()` lifecycle? `Database.close()` closes the one connection; no per-store close needed.

## Notes

**Effort:** Medium — comparable to LKPR-50 in scope. The fixture changes in tests are the most fiddly part.

**Not in scope — `_row_to_memory` deduplication:** The `_row_to_memory()` function in `orchestrator.py` does the same `{keys()}` guard dance as `_row_to_link` in `link_store.py`. Since stores return dict-shaped rows (not typed models), both converters stay where they are for now. Cleaning this up is bundled with the typed-model follow-up ticket.

**Migration data loss risk:** The old `_migrate_dedup_links()` and `_migrate_dedup_memories()` delete rows. In the new versioned system, these become irreversible numbered migrations — document them clearly so nobody accidentally runs them on a production store.
