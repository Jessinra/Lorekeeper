# LKPR-51 — LinkStore decomposition: split god object into focused data stores

**Status:** Proposal — not yet implemented
**Filed:** 2026-05-31 by Diana
**Depends on:** LKPR-50 (dashboard tests must be merged first for regression net)

## Execution Plan

### Strategy

Move in three phases, each independently testable:

1. **Create `Database` class** — shared SQLite connection + versioned migration runner. No behavioral change; the old `LinkStore._migrate()` chain moves into numbered migration functions.
2. **Extract focused stores** — `MemoryStore`, `ReflectionStore`, `MetricsStore`, `ConfigStore`. Each extracted as a new file, each taking `Database` instead of a path. `LinkStore` shrinks to link-only CRUD.
3. **Rewrite wiring** — `server.py` `init_service()`, `orchestrator.py` `MemoryService.__init__`, `dashboard/app.py` call sites. All stores wired through `MemoryService`.

### Phase 1 — Database class

**File:** `src/lorekeeper/services/database.py`

```python
import sqlite3
from pathlib import Path
from datetime import UTC, datetime

MIGRATIONS: list[tuple[int, str, str]] = [
    # Migration 1 — initial schema (all CREATE TABLE IF NOT EXISTS)
    # This is idempotent — only creates missing tables.
    (1, "initial_schema", """
        CREATE TABLE IF NOT EXISTS memories (
          id               TEXT PRIMARY KEY,
          title            TEXT NOT NULL,
          description      TEXT NOT NULL,
          content          TEXT NOT NULL,
          created_at       TEXT NOT NULL,
          updated_at       TEXT NOT NULL,
          usage_count      INTEGER NOT NULL DEFAULT 0,
          score            REAL    NOT NULL DEFAULT 1.0,
          soft_deleted     INTEGER NOT NULL DEFAULT 0,
          confidence       REAL,
          confidence_count INTEGER NOT NULL DEFAULT 0,
          last_used        TEXT,
          namespace        TEXT    NOT NULL DEFAULT 'shared'
        );
        CREATE INDEX IF NOT EXISTS idx_memories_soft_deleted ON memories(soft_deleted);
        CREATE TABLE IF NOT EXISTS memory_links (
          id                TEXT PRIMARY KEY,
          source_memory_id  TEXT NOT NULL,
          target_memory_id  TEXT NOT NULL,
          relation_type     TEXT NOT NULL,
          reason            TEXT NOT NULL,
          score             REAL    NOT NULL DEFAULT 1.0,
          created_at        TEXT    NOT NULL,
          updated_at        TEXT    NOT NULL,
          usage_count       INTEGER NOT NULL DEFAULT 0,
          confidence        REAL,
          confidence_count  INTEGER NOT NULL DEFAULT 0,
          FOREIGN KEY (source_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
          FOREIGN KEY (target_memory_id) REFERENCES memories(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_links_source ON memory_links(source_memory_id);
        CREATE INDEX IF NOT EXISTS idx_links_target ON memory_links(target_memory_id);
        CREATE TABLE IF NOT EXISTS reflections (
          id            TEXT PRIMARY KEY,
          session_id    TEXT NOT NULL UNIQUE,
          topic         TEXT,
          summary       TEXT NOT NULL,
          task_type     TEXT,
          factual_discoveries TEXT,
          lessons_learnt      TEXT,
          good_patterns       TEXT,
          decisions           TEXT,
          user_profile_updates TEXT,
          memory_ids          TEXT,
          created_at    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          id                TEXT PRIMARY KEY,
          reflection_id     TEXT,
          title             TEXT,
          when_text         TEXT,
          model             TEXT,
          source            TEXT,
          transcript        TEXT,
          summary           TEXT,
          what_was_done     TEXT,
          decisions         TEXT,
          lessons_learnt    TEXT,
          good_patterns     TEXT,
          user_profile      TEXT,
          discoveries       TEXT,
          FOREIGN KEY (reflection_id) REFERENCES reflections(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS api_metrics (
          id           INTEGER PRIMARY KEY AUTOINCREMENT,
          tool_name    TEXT NOT NULL,
          called_at    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS config_overrides (
          key         TEXT PRIMARY KEY,
          value       TEXT NOT NULL,
          updated_at  TEXT NOT NULL
        );
    """),
    # Migration 2 — deduplicate links + add unique pair constraint
    (2, "dedup_links", """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_links_unique_pair
        ON memory_links(source_memory_id, target_memory_id, relation_type);
        DELETE FROM memory_links WHERE rowid NOT IN (
            SELECT MIN(rowid) FROM memory_links
            GROUP BY source_memory_id, target_memory_id, relation_type
        );
    """),
    # Migration 3 — deduplicate memories by title (keep highest score)
    (3, "dedup_memories", """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_unique_title ON memories(title);
        DELETE FROM memories WHERE rowid NOT IN (
            SELECT rowid FROM memories m1
            WHERE rowid = (
                SELECT rowid FROM memories m2
                WHERE m2.title = m1.title
                ORDER BY m2.score DESC, m2.created_at ASC
                LIMIT 1
            )
        );
    """),
    # Migration 4 — add session content columns (transcript, decisions, etc.)
    (4, "session_content_columns", """
        ALTER TABLE sessions ADD COLUMN transcript TEXT;
        ALTER TABLE sessions ADD COLUMN what_was_done TEXT;
        ALTER TABLE sessions ADD COLUMN decisions TEXT;
        ALTER TABLE sessions ADD COLUMN lessons_learnt TEXT;
        ALTER TABLE sessions ADD COLUMN good_patterns TEXT;
        ALTER TABLE sessions ADD COLUMN user_profile TEXT;
        ALTER TABLE sessions ADD COLUMN discoveries TEXT;
    """),
    # Migration 5 — add last_used column to memories
    (5, "add_last_used_column", """
        ALTER TABLE memories ADD COLUMN last_used TEXT;
    """),
    # Migration 6 — add namespace column to memories
    (6, "add_namespace_column", """
        ALTER TABLE memories ADD COLUMN namespace TEXT NOT NULL DEFAULT 'shared';
    """),
    # Migration 7 — switch unique title index to namespace-scoped
    (7, "namespace_unique_title", """
        DROP INDEX IF EXISTS idx_memories_unique_title;
        CREATE UNIQUE INDEX idx_memories_unique_title ON memories(namespace, title);
    """),
]


class Database:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.commit()

    def migrate(self) -> None:
        """Apply pending migrations in version order, each in its own transaction."""
        # Create schema version table if not present
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_version (version INTEGER PRIMARY KEY, applied_at TEXT)"
        )
        current = self._conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM _schema_version"
        ).fetchone()[0]

        for version, name, sql in MIGRATIONS:
            if version > current:
                self._conn.executescript(sql)
                self._conn.execute(
                    "INSERT INTO _schema_version (version, applied_at) VALUES (?, ?)",
                    (version, datetime.now(UTC).isoformat()),
                )
                self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, rows: list[tuple]) -> sqlite3.Cursor:
        return self._conn.executemany(sql, rows)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
```

**Key decisions:**
- Migration SQL is inline in the `MIGRATIONS` list, not separate files. Each migration entry includes the full DDL or DML. Simpler at this scale — no migration-directory scaffolding needed.
- Each migration runs in its own transaction (via `executescript` + explicit `commit`). If one fails mid-chain, earlier migrations are already committed. Acceptable for a local-first DB — manual recovery is straightforward.

**Tests:**
- `tests/test_database.py` — verify migration 1 creates all tables, migration chain is idempotent, rolling forward from any version works
- Existing `test_link_store.py` tests still pass because `Database` returns the same `sqlite3.Row`-factory connection

### Phase 2 — Extract focused stores

Each store follows the same pattern:

```python
class MemoryStore:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_memory_row(self, id, title, ...) -> None: ...
    def get_memory_row(self, id, namespaces=None) -> dict | None: ...
    ...
```

**Extraction mapping:**

```
LinkStore.upsert_memory_row          → MemoryStore.upsert_memory_row
LinkStore.get_memory_row             → MemoryStore.get_memory_row
LinkStore.get_memory_row_by_title    → MemoryStore.get_memory_row_by_title
LinkStore.all_memory_rows            → MemoryStore.all_memory_rows
LinkStore.update_memory_fields       → MemoryStore.update_memory_fields
LinkStore.delete_memory_row          → MemoryStore.delete_memory_row

LinkStore.insert_link                → LinkStore.insert_link (stays)
LinkStore.links_for_memory           → LinkStore.links_for_memory (stays)
LinkStore.get_link                   → LinkStore.get_link (stays)
LinkStore.update_link_fields         → LinkStore.update_link_fields (stays)
LinkStore.all_links                  → LinkStore.all_links (stays)
LinkStore.delete_link                → LinkStore.delete_link (stays)
LinkStore._row_to_link               → LinkStore._row_to_link (stays)

LinkStore.insert_reflection          → ReflectionStore.insert_reflection
LinkStore.get_reflection             → ReflectionStore.get_reflection
LinkStore.all_reflections            → ReflectionStore.all_reflections
LinkStore.upsert_session             → ReflectionStore.upsert_session
LinkStore.upsert_sessions_bulk       → ReflectionStore.upsert_sessions_bulk
LinkStore.all_processed_session_ids  → ReflectionStore.all_processed_session_ids
LinkStore.all_sessions               → ReflectionStore.all_sessions
LinkStore.sessions_with_content      → ReflectionStore.sessions_with_content
LinkStore.get_session                → ReflectionStore.get_session
LinkStore.sessions_for_reflection    → ReflectionStore.sessions_for_reflection

LinkStore.increment_metric           → MetricsStore.increment_metric
LinkStore.get_metrics                → MetricsStore.get_metrics

LinkStore.get_config_overrides       → ConfigStore.get_overrides
LinkStore.set_config_override        → ConfigStore.set_override
LinkStore.delete_config_override     → ConfigStore.delete_override
```

**Return types:** Start with dict-shaped results (compatible with current callers). Convert to typed `Memory`/`MemoryLink` models in a follow-up — the decomposition diff is already big enough without changing the type contract.

**`LinkStore` after extraction:** ~150 lines (link-only CRUD + `_row_to_link`). File keeps its name but loses 75% of its content.

**Tests:**
- `tests/test_link_store.py` — adapt fixtures to pass `Database` instead of `Path`, but all existing test cases stay the same
  - **Fixture split**: Current fixture seeds via `store.upsert_memory_row()` (a LinkStore method before extraction). After decomposition, the fixture pattern becomes:
    ```python
    @pytest.fixture
    def link_store(tmp_path):
        db = Database(tmp_path / "test.db")
        db.migrate()
        ls = LinkStore(db)
        ms = MemoryStore(db)
        # seed FK targets via MemoryStore
        for i in ("a", "b", "c"):
            ms.upsert_memory_row(...)
        yield ls, ms, db
        db.close()
    ```
  - Note: `test_cascade_delete` (seeds via `LinkStore.upsert_memory_row()` then deletes) becomes `ms.delete_memory_row()`. The test pairing conceptually crosses stores — written as a `LinkStore` test because it validates FK cascade behavior.
- `tests/test_memory_store.py` — new file, can be thin (LinkStore memory tests already cover this)
- `tests/test_reflection_store.py` — new file for session/reflection CRUD
- `tests/test_config_store.py` — new file for override round-trips

### Phase 3 — Rewire everything

**`server.py` `init_service()`:**

```python
def init_service(settings: Settings | None = None) -> MemoryService:
    global _svc
    s = settings or Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)

    engine = build_engine(s.vector_store, s.chroma_path, s.lancedb_path, s.embedding_model)
    engine.probe_score_scale()

    db = Database(s.sqlite_path)
    db.migrate()

    memories = MemoryStore(db)
    links = LinkStore(db)
    reflections = ReflectionStore(db)
    metrics = MetricsStore(db)
    config = ConfigStore(db)

    # Apply persisted config overrides
    overrides = config.get_overrides()
    ...

    kw = KeywordIndex()
    svc = MemoryService(engine, memories, links, reflections, metrics, config, kw, s)
    ...
    _svc = svc
    return svc
```

**`orchestrator.py`:**

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
    ) -> None:
        self._engine = engine
        self._memories = memories
        self._links = links
        self._reflections = reflections
        self._metrics = metrics
        self._config = config
        self.settings = settings   # public — dashboard accesses via get_service().settings
        self._kw = keyword_index
        ...
```

All internal references:
- `self._store.upsert_memory_row(...)` → `self._memories.upsert_memory_row(...)`
- `self._store.insert_link(...)` → `self._links.insert_link(...)`
- `self._store.increment_metric(...)` → `self._metrics.increment_metric(...)`
- `self._store.insert_reflection(...)` → `self._reflections.insert_reflection(...)`
- etc. (21 call sites total in orchestrator.py)

**`dashboard/app.py`:**

All 17 `get_service()._store.*` call sites (plus 2 `get_service()._settings` accesses for settings data) become typed store accesses. The orchestrator exposes stores as public attributes (not prefixed with `_`):

```python
store = get_service().links          # was: get_service()._store
store = get_service().memories       # was: get_service()._store
store = get_service().config         # was: get_service()._store.get_config_overrides()
store = get_service().reflections    # was: get_service()._store
store = get_service().metrics        # was: get_service()._store
settings = get_service().settings    # was: get_service()._settings
```

This also fixes the dashboard's private-attribute access — it was using `_store` and `_settings` because the orchestrator didn't expose individual stores or settings as public attributes.

## Risk Items

- **Migration ordering:** The current `_migrate()` chain runs in a specific order (dedup_links → dedup_memories → session_content → last_used → namespace → namespace_unique_title). The numbered migration list must preserve this order exactly. A migration that creates the `idx_memories_unique_title` index after adding the namespace column is order-dependent.
- **Destructive migrations:** `_migrate_dedup_links` and `_migrate_dedup_memories` DELETE rows. These must be clearly documented in the code as version 0-level migrations that only run on fresh databases. On existing databases they're no-ops (already applied). The versioned system naturally handles this — they become migrations 2 and 3 that won't re-run.
- **Thread safety:** The shared `Database` object passes a single connection. `check_same_thread=False` is already set. If multi-threaded access is ever needed, a connection pool would be required — but that's out of scope for this ticket.
- **`close()` lifecycle:** Currently `LinkStore.close()` closes its connection. With a shared `Database`, one `db.close()` replaces all per-store close calls. Check if any code path calls `close()` on individual stores (grep `_store.close()` in the codebase).

## Verification

1. `uv run pytest -v` — full suite green, same 121+ test count
2. `uv run pytest -v tests/test_database.py` — migration tests pass
3. Dashboard launches and all tabs (memories, links, sessions, reflections, config, metrics) load without errors
4. `lore_search`, `lore_remember`, `lore_insert`, `lore_update`, `lore_reflect` all work (smoke test)
5. Config overrides survive restart (set in dashboard → restart server → value persists)
6. No import errors from deleted/renamed modules
7. `git diff --stat` shows the LinkStore file dropped from 637 lines to ~150

## Per-File Change Summary

| File | Before | After | Delta |
|---|---|---|---|
| `services/link_store.py` | 637 lines | ~150 lines | -487 |
| `services/database.py` | — | ~100 lines | +100 |
| `services/memory_store.py` | — | ~120 lines | +120 |
| `services/reflection_store.py` | — | ~100 lines | +100 |
| `services/metrics_store.py` | — | ~60 lines | +60 |
| `services/config_store.py` | — | ~40 lines | +40 |
| `services/orchestrator.py` | 730 lines | ~740 lines | +10 (imports + type hints) |
| `server.py` | 171 lines | ~190 lines | +20 (wiring) |
| `dashboard/app.py` | 389 lines | ~389 lines | ±0 (rewrite lines, no line count change) |
| `tests/test_link_store.py` | 162 lines | ~162 lines | ±0 (fixture changes, same test count) |
| `tests/test_database.py` | — | ~60 lines | +60 |
| _Total_ | | | _~2,089 → ~2,111_ |

The diff looks bigger than it is — most of the `+` is extracted code from `link_store.py` that's being moved, not new logic.
