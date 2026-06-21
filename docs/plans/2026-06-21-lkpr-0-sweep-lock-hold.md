# LKPR-0 — Minimize SQLite writer-lock hold time in the sweep

**Date:** 2026-06-21
**Branch:** `fix/wal-shutdown-cleanup`
**Type:** bugfix / concurrency hardening

## Problem

Lorekeeper shows "failed" on new Hermes sessions due to SQLite
`database is locked`. Two compounding causes, both proven live this session
(`lore_remember` returned `database is locked` 3× while two Diana MCP servers
were alive on `~/.lorekeeper/profile/diana/lorekeeper.db`):

1. **No `busy_timeout`** — `Database.__init__` sets `journal_mode=WAL` +
   `foreign_keys=ON` but never `busy_timeout`. Default is 0 → first write under
   contention raises instantly, no retry. (Safety net.)

2. **Sweep holds the writer lock across slow ML work (the lock hog).**
   `SweepService.run()` (sweep*service.py:61) opens an implicit write
   transaction on the first `upsert_suggestion` (line 126) and does NOT commit
   until line 161 — \_after* iterating all memories. Between upserts it calls
   `self._generator.generate(mem_id)` (line 97), which runs embeddings + spaCy
   NER + BM25 (~hundreds of ms each). So the single writer lock is held for the
   entire scan (minutes for 728 memories) while doing work that needs no lock.
   This is why the WAL grew to 3 MB and a write probe timed out after 3 s.

## Goal

Acquire the writer lock **only** for the write burst, release immediately.
All slow compute (`generate()`) happens with no open write transaction.

## Changes

### 1. `src/lorekeeper/services/database.py` — busy_timeout + PASSIVE checkpoint

`__init__` (currently lines 482–492). Set `busy_timeout` as the FIRST pragma
after connect (before any I/O), and change the startup checkpoint
`TRUNCATE → PASSIVE` (TRUNCATE needs an exclusive lock it can't get under
concurrency; PASSIVE never blocks).

```python
self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
self._conn.row_factory = sqlite3.Row
self._conn.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")   # ← FIRST, before any I/O
self._conn.execute("PRAGMA journal_mode = WAL")
self._conn.execute("PRAGMA foreign_keys = ON")
self._conn.commit()
# startup checkpoint: PASSIVE never blocks under concurrency
self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
```

- `_CHECKPOINT_SQL` const (line 33): `TRUNCATE` → `PASSIVE`.
- Add `busy_timeout_ms: int = 5000` param to `Database.__init__` (default
  preserves behaviour for all existing callers; server.py can pass
  `s.busy_timeout_ms`).
- The drained-pages log guard stays; PASSIVE returns `(busy, log_pages,
checkpointed_pages)` same shape.

### 2. `src/lorekeeper/config.py` — make timeout configurable

Add after `data_dir`/`log_dir` block:

```python
busy_timeout_ms: int = Field(
    default=5000,
    description="SQLite busy_timeout in ms — wait-for-lock before erroring (LORE_BUSY_TIMEOUT_MS)",
)
```

### 3. `src/lorekeeper/server.py` — pass busy_timeout to both Databases

`Database(s.sqlite_path)` at line 56 (main) and line 121 (sweep) →
`Database(s.sqlite_path, busy_timeout_ms=s.busy_timeout_ms)`.

### 4. `src/lorekeeper/services/sweep_service.py` — split compute from write (THE fix)

Restructure `run()` into two phases:

- **Phase 1 (read/compute, NO write txn held):** scan memories, call
  `generate()` for each, filter against `linked_pairs`/`rejected`, and collect a
  list of plain dicts/tuples describing the suggestions to upsert. Tally stats.
  No `upsert_suggestion`, no `commit` here. The connection issues only SELECTs,
  which in WAL never take the writer lock.

- **Phase 2 (write burst, lock held briefly then released):** iterate the
  collected results calling `upsert_suggestion(...)`, then `prune_expired(...)`,
  then a single `self._conn.commit()`. The implicit BEGIN fires on the first
  upsert and commit releases — lock held only for the fast INSERTs, no ML work
  in between.

`_increment_metric` (line 67 call) stays as-is — it commits its own tiny write
before Phase 1 begins, so no write txn is left dangling into the compute phase.

Behaviour unchanged: same suggestions written, same stats dict, same prune. Only
the lock-hold window shrinks from "whole scan" to "insert burst."

## Tests

New file `tests/test_sweep_lock_hold.py`:

1. **`test_sweep_no_write_lock_during_generate`** — instrument by making a
   `generate()` stub that, when called, asserts the DB has no pending write by
   opening a _second_ connection (busy_timeout=0) and successfully doing
   `BEGIN IMMEDIATE; ROLLBACK`. If the sweep held the writer lock during
   generate, BEGIN IMMEDIATE would raise `database is locked`. Proves the lock
   is free during compute.
2. **`test_sweep_still_writes_suggestions`** — run sweep end-to-end against a
   real temp DB with 3 memories + a fake generator returning one candidate;
   assert the suggestion lands in `link_suggestions` (behaviour preserved).
3. **`test_database_sets_busy_timeout`** — open a `Database`, assert
   `PRAGMA busy_timeout` reads back 5000 (and a custom value when passed).

Reuse `tests/_helpers.build_stores`. FakeEngine/FakeGenerator pattern from
`tests/test_pr237_review_fixes.py`.

## Verification

- `uv run pytest tests/test_sweep_lock_hold.py tests/test_database.py -q`
- `uv run pytest -q` (full suite — no regressions)
- `uv run mypy src`
- Manual: `scripts/sqlite_lock_repro.py` already proves busy_timeout behaviour.

## Out of scope

- Single-instance process cleanup (`_cleanup_stale_instances`) — secondary
  mitigation, separate concern. busy_timeout + short locks is the durable fix.
