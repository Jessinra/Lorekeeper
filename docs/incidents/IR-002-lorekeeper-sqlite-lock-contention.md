# IR-002: Lorekeeper SQLite Lock Contention — "failed" on Hermes Initialization

**Status:** Resolved
**Severity:** P0 (blocking new Hermes sessions from using lorekeeper)
**Date:** 2026-06-21
**Author:** Diana
**Fix PR:** #240 (emergency merge), #241 (post-incident)

---

## Summary

Lorekeeper MCP servers showed "failed" status in Hermes session initialization. The incident was a **cascade of five independent bugs** — each on its own survivable, but together they created a perfect storm of lock contention. At peak, 5+ zombie MCP processes were each crashing and restarting the sweep every 5 minutes, saturating CPU at 113%.

The fix had two rounds:

| Round       | When                  | What                                                                                      |
| ----------- | --------------------- | ----------------------------------------------------------------------------------------- |
| **PR #240** | 10:23 SGT (emergency) | `busy_timeout=5000`, WAL checkpoint fix, sweep two-phase write                            |
| **PR #241** | Post-incident         | `config_store.py` commit, scheduler retry guard, **DB split** (sweep gets own `.db` file) |

The structural fix — separating sweep writes to `sweep.db` — eliminates this class of incident entirely.

---

## Timeline

| Time (SGT)  | Event                                                                                                                      |
| ----------- | -------------------------------------------------------------------------------------------------------------------------- |
| ~08:48      | First MCP sessions start. PR #237 (sweep engine) is live.                                                                  |
| 09:19       | **Report:** Lorekeeper "failed" in Hermes init. Investigation begins.                                                      |
| 09:19–09:23 | Root cause traced: `wal_checkpoint(TRUNCATE)` + `busy_timeout=0`.                                                          |
| 09:23       | PID 32703 at **113% CPU** — 5+ concurrent lorekeeper processes.                                                            |
| 09:39       | Deeper investigation confirms via repro: `busy_timeout=0` → instant crash; `busy_timeout=5000` → waits 0.87s and succeeds. |
| 09:39–10:23 | Fix refined: sweep two-phase split, PASSIVE checkpoint, separate DB connection.                                            |
| 10:23       | **PR #240 merged** — busier servers start recovering.                                                                      |
| 10:40–10:41 | New servers spawn with fix. 4 zombies still alive but no longer crashing.                                                  |
| ~11:00      | Post-incident: `config_store.py` commit, retry guard, DB split. Skills/checklists updated.                                 |

---

## Root Causes — A Causal Chain

This was not one bug but **five**, each a link in a chain. The chain broke when you could trace from any link to the user-visible symptom (MCP "failed").

### 🥇 Link 1: The Trigger — Sweep shared the same SQLite connection as MCP (thread-unsafe)

PR #237 (the sweep engine) created its `MemoryStore` and `LinkStore` from the **same** `sqlite3.Connection` as the main MCP thread (`check_same_thread=False`, zero synchronisation). Two threads calling `execute()` on the same connection can corrupt in-memory transaction state — Python's `sqlite3` has no internal locking.

**Why this caused today's crash:** The sweep's `generate()` does embeddings + spaCy + BM25 — ML work that takes seconds. While the sweep held the implicit writer lock (from a prior `upsert`), the MCP thread couldn't write. But more critically, the corrupt shared connection caused the sweep itself to crash mid-run with an internal SQLite error — the first domino.

**Evidence:** `link_suggestions: 0 rows`, no `lore_sweep` metric, no `sweep_next_run_at` key — the sweep never completed once.

---

### 🥈 Link 2: The Proximate Failure — `busy_timeout=0` (SQLite default)

`Database.__init__` set `journal_mode=WAL` and `foreign_keys=ON` but never `PRAGMA busy_timeout`. SQLite's default is **0 milliseconds**: the very first write overlap raises `OperationalError: database is locked` instantly with zero retry.

**Why this amplified link 1:** The shared-connection crash from link 1 released the WAL write lock. When the MCP server (or a zombie) tried its next write, it hit `busy_timeout=0` → instant `database is locked` → the MCP connection handler propagated this as a RuntimeError → Hermes showed lorekeeper as "failed". The write bursts from 5+ concurrent processes meant someone always had the lock.

---

### 🥉 Link 3: The Amplifier — Timer-advance-after-job → infinite retry storm

`PeriodicJob._loop` set `sweep_next_run_at` **after** the job callback returned. If the job crashed (which link 1 guaranteed), the timer was never written → on the next 300s poll the timer appeared expired → the job restarted → crashed → restarted → ...

**Why this turned a crash into a disaster:** Every zombie MCP server ran its own sweep scheduler. With 5+ zombies and 300s poll, the sweep was crashing every 5 minutes per zombie — that's one crash per minute, continuously, from ~08:48 until the fix at 10:23. PID 32703 at 113% CPU confirms the retry storm.

---

### 🔗 Link 4: The Force Multiplier — `uv` zombie accumulation

Hermes spawns MCP servers via `uv run --directory ... lorekeeper`. When Hermes reloads (new session, config change), it sends EOF to the old process's stdin. But `uv` swallows stdin-EOF — the underlying `lorekeeper` process never sees it and survives as a zombie. Each zombie keeps its own SQLite connection, runs its own sweep scheduler, and loads the ~90MB embedding model.

**Why this made everything worse:** 5+ zombies × infinite retries (link 3) × slow sweep ML work (link 1) = sustained write contention that kept every process fighting for the same SQLite lock. Without zombies, even the timer-after-job bug could only cause one crash per 300s.

---

### 🚫 Link 5: The Latent Bug — missing `commit()` in ConfigStore (did NOT cause this incident)

`set_override()` and `delete_override()` executed DML without `commit()`. Changes sat in Python's in-memory transaction buffer — the same connection read them back, but `.db` file never got them. The dashboard worked fine because it calls `svc.commit()` externally.

**Why this is included:** If the sweep had survived the crash and called `set_override` to write its timer, that write would have been lost on the next process restart. It's a data-loss bug that tests never caught because the same connection reads its own uncommitted buffer.

---

## How the Causal Chain Works

```
[Shared connection crash] ─→ [busy_timeout=0 → instant error]
         │                            │
         │                            └──→ MCP shows "failed" to user
         │
         └──→ [Timer never set after crash → infinite retries]
                        │
                        └──→ [5+ zombies amplify → 5 crashes/minute → 113% CPU]
                                        │
                                        └──→ Every MCP init hits lock contention

[Missing commit] ─── dormant, would trigger on next restart after a timer write
```

**Three of these five links changed in a single session.** Each fix independently breaks the chain:

| Fix                                 | Which link it breaks | Why it suffices alone                                                    |
| ----------------------------------- | -------------------- | ------------------------------------------------------------------------ |
| `busy_timeout=5000`                 | Link 2               | Even on write overlap, each connection waits up to 5s — no instant crash |
| Sweep gets own connection + DB file | Link 1               | Zero shared state between threads; structurally impossible               |
| Timer-before-job                    | Link 3               | Crash → 11 min retry, not infinite loop                                  |
| Drop `uv` from spawn chain          | Link 4               | No zombies → no retry storm                                              |

---

## Impact

- **Duration:** ~1 hour (09:19 report to 10:23 PR #240 merge). Sweep engine was crashing since ~08:48.
- **Scope:** Every Hermes session starting during the window showed lorekeeper as "failed"
- **Data integrity:** No data loss. Contention blocked new connections; existing sessions continued
- **User-facing:** Jason had to work around failed MCP initialization repeatedly

---

## Detection

- **User report:** Jason's `/reload-mcp` showed lorekeeper status "failed" at 09:19
- **Live confirmation:** `lore_remember` tool calls in the investigation session itself failed 3× with `database is locked`
- **Process evidence:** `ps aux` showed 5+ concurrent lorekeeper processes, PID 32703 at **113% CPU**

---

## Fixes Applied

### PR #240 (`d31dfb0`, merged 10:23) — 7 files, +382/-43

| Change                       | File(s)                             | What it does                                                                           |
| ---------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------- |
| `PRAGMA busy_timeout = 5000` | `services/database.py`              | Wait up to 5s for lock instead of crashing instantly                                   |
| `wal_checkpoint(PASSIVE)`    | `services/database.py`              | Never blocks — checkpoints what it can without exclusive lock                          |
| Sweep two-phase split        | `services/sweep_service.py`         | Compute first (no lock), then burst-write (milliseconds lock)                          |
| Separate sweep DB connection | `services/database.py`, `server.py` | Sweep gets its own `Database` instance → separate connection → no thread-safety issues |
| `atexit` cleanup             | `services/database.py`              | Clean connection close on SIGTERM                                                      |

### PR #241 — Post-incident code fixes

| Change                                    | File(s)                                          | What it does                                                                                                                                                | Which link it breaks |
| ----------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| `commit()` in `ConfigStore`               | `services/config_store.py`                       | Data loss protection on DML                                                                                                                                 | Link 5               |
| Retry timer before job                    | `scheduler.py`                                   | Crash → 11 min retry, not infinite                                                                                                                          | Link 3               |
| **DB split** — sweep writes to `sweep.db` | `config.py`, `services/database.py`, `server.py` | Sweep's `link_suggestions`, `api_metrics`, and timer config live in `~/.lorekeeper/sweep.db`. Reads from `lorekeeper.db` via separate read-only connection. | Structural — Link 1  |

The DB split is the most important post-incident change. Before, both threads wrote to `lorekeeper.db` through separate connections — SQLite's `busy_timeout` handled contention, but contention still existed at the file-locking layer. Now the sweep **never writes to `lorekeeper.db`**. Its write bursts go to `sweep.db`, and the MCP server never touches `sweep.db`. Zero contention, full stop.

### Skills + checklist updates (same session)

**`lorekeeper-code-reviewer`** (v1.13.0):

- BLOCKER #16: missing `commit()` after DML
- BLOCKER #17: shared SQLite connection across threads
- BLOCKER #18: timer-after-job pattern
- References updated

**`github-code-review`** (v1.6.0):

- 3 new correctness checklist items matching the BLOCKERs

### Deferred

- **Drop `uv` from MCP spawn chain** — eliminate zombie source. Config change to point `.venv/bin/lorekeeper` directly. P0 deferred per Jason.

---

## Action Items

| #   | Action                                                                                                                                               | Owner       | Status   |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | -------- |
| 1   | `config_store.py`: add `commit()` after `set_override()` and `delete_override()`                                                                     | Diana       | DONE     |
| 2   | `scheduler.py`: retry timer before job, full interval on success                                                                                     | Diana       | DONE     |
| 3   | **DB split**: sweep writes to `sweep.db`, reads from main DB connection                                                                              | Diana       | DONE     |
| 4   | Document `sweep_sqlite_path` in `config.py`                                                                                                          | Diana       | DONE     |
| 5   | Add BLOCKER patterns to code-reviewer (#16 missing commit, #17 shared connection, #18 timer-after-job, #19 sweep DB)                                 | Diana       | DONE     |
| 6   | Add checklist items to `github-code-review`: SQLite commit-after-write, background-thread connection isolation, timer-before-job, sweep-dedicated DB | Diana       | DONE     |
| 7   | Create `postmortem-writing` repo skill documenting IR template and mandated deliverables                                                             | Diana       | DONE     |
| 8   | Drop `uv` from MCP spawn chain                                                                                                                       | Diana/Jason | DEFERRED |

---

## Lessons Learned

### How the chain teaches us

1. **`busy_timeout=0` is SQLite's most treacherous default.** Always set it explicitly on shared databases. WAL improves concurrent reads but does not prevent write contention.

2. **Never do ML work inside a write transaction.** Collect payloads first, then burst-write in milliseconds. The writer lock should be acquired for **microseconds**, not seconds.

3. **Timer must be set before the job, not after.** A crash between job completion and timer write creates an infinite retry storm. If the timer was set before the job, a retry happens after N minutes — bounded.

4. **Every SQLite DML must have an explicit `commit()`.** The same connection reads from its transaction buffer, so missing commits pass all tests (the read-back works!) but lose data on process crash.

5. **Background threads must never share a `sqlite3.Connection`.** `check_same_thread=False` removes the Python guard but not the race condition.

6. **Separate databases for separate workloads.** If process A and process B both write to SQLite, put them in different `.db` files. This eliminates the OS/file-system locking layer entirely. `busy_timeout` is a band-aid; a separate file is the structural cure.

7. **Postmortems must encode lessons into skills + review checklists.** Without this, the same bug class passes review again. Every BLOCKER pattern in this incident was available at code review — it just wasn't checked against.

---

## Related

- PR #237 — introduced sweep engine + missing commit (regression source)
- PR #240 — fix: busy_timeout, PASSIVE checkpoint, sweep two-phase split
- PR #241 — post-incident: config_store commit, retry guard, DB split
- Commit `ff3639c4` — original `ConfigStore` without `commit()`
- `src/lorekeeper/services/config_store.py` — missing commit fix
- `src/lorekeeper/scheduler.py` — timer-before-job fix
- `src/lorekeeper/services/database.py` — `SWEEP_SCHEMA`, `apply_sweep_schema()`
- `src/lorekeeper/config.py` — `sweep_sqlite_path` property
- `src/lorekeeper/server.py` — sweep uses `sweep.db`
- `.hermes/skills/postmortem-writing/SKILL.md` — repo skill for writing postmortems
- `lorekeeper-code-reviewer` references/blocker-patterns.md — patterns #16, #17, #18, #19
- `github-code-review` SKILL.md — checklist items
- `docs/incidents/IR-001-docs-ci-deploy.md` — previous incident report
- `docs/engineering/postmortem-writing.md` — postmortem writing guide (causal chain format, must-have deliverables)
- `docs/engineering/code-review-blocker-patterns.md` — BLOCKER patterns #16–#19 encoded from this incident
- `docs/engineering/qa-verification-sweep-db.md` — QA protocol for sweep DB integrity checks
