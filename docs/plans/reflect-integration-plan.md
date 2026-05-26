# Plan: Reflect Integration into Lorekeeper

## Context

The `/reflect` skill processes past session transcripts into structured learnings and persists them to Lorekeeper. Currently it is **not integrated** with the ecosystem:

- Processed sessions are tracked in a flat text file (`loop/processed_sessions.txt`)
- The structured reflection output is discarded after writing memories
- There is no dashboard visibility into what the agent has learned

This plan adds a proper first-class `Reflection` entity, a new MCP tool for submitting reflections, and replaces the Runs tab with a Reflections tab in the dashboard.

---

## New SQLite Tables

### `sessions` — replaces `processed_sessions.txt`

```sql
CREATE TABLE sessions (
  session_id    TEXT PRIMARY KEY,  -- UUID from session file frontmatter
  session_date  TEXT,              -- ISO date when the session happened
  topic         TEXT,              -- short topic description
  task_type     TEXT,              -- build / debug / review / design
  reviewed_at   TEXT NOT NULL,     -- when /reflect processed this session
  reflection_id TEXT,              -- FK → reflections.id (nullable)
  FOREIGN KEY (reflection_id) REFERENCES reflections(id) ON DELETE SET NULL
);
```

### `reflections` — new first-class entity

```sql
CREATE TABLE reflections (
  id                   TEXT PRIMARY KEY,  -- UUID
  created_at           TEXT NOT NULL,     -- when submitted
  session_count        INTEGER NOT NULL,  -- number of sessions covered
  lessons_learnt       TEXT NOT NULL,     -- markdown / bullet list
  good_patterns        TEXT,             -- what worked well (keep doing)
  user_profile_updates TEXT,             -- observations about the user
  factual_discoveries  TEXT,             -- domain facts, decisions, constraints
  summary              TEXT NOT NULL,    -- 1-2 sentence overview
  memory_ids           TEXT             -- JSON array of lore UUIDs created
);
```

---

## New MCP Tool: `lore_reflect`

Agent calls this at the end of every `/reflect` run. Writes one row to `reflections` and marks all covered session IDs in `sessions`.

### Input

```python
sessions:              list[str]  # session_ids covered
session_dates:         list[str]  # parallel — ISO dates (can be empty strings)
session_topics:        list[str]  # parallel — topic labels (can be empty strings)
lessons_learnt:        list[str]  # corrections / what to do differently next time
good_patterns:         list[str]  # what worked well
user_profile_updates:  list[str]  # observations about the user's style/preferences
factual_discoveries:   list[str]  # non-obvious domain facts, API behaviour, decisions
summary:               str        # 1-2 sentence overview of the reflection
memory_ids:            list[str]  # lore UUIDs created/updated in this reflect run
```

### Output

```json
{
  "reflection_id": "uuid",
  "sessions_marked": 3,
  "created_at": "2026-05-19T12:00:00Z"
}
```

Sessions are automatically upserted into the `sessions` table and linked to the reflection.
No more writes to `processed_sessions.txt`.

---

## Migration

On first startup, if the `sessions` table is empty and `loop/processed_sessions.txt` exists,
backfill each UUID as a session row with only `session_id` and `reviewed_at = NOW()`.
All other fields left NULL. The txt file is not deleted — just no longer written to.

---

## Dashboard Changes

### Tab Layout

Replace the **Runs** tab with a **Reflections** tab. The cron run history (old `runs.js` content)
is demoted to a collapsible secondary section within the same tab — it can be removed entirely
once the reflect skill is generating data regularly.

```
Memories | Detail | Links | Query | Reflections | Config | Backup
                                    ↑ replaces Runs
```

### Reflections Tab Layout

**Header metrics:**

- Total reflections · Total sessions reviewed · Last reflected date

**Reflections table** (primary, top):

| Date       | Sessions | Summary | Memories Created |
| ---------- | -------- | ------- | ---------------- |
| 2026-05-19 | 5        | ...     | 3                |

**Click row → detail panel expands below table:**

- **Summary** — full text
- **Lessons Learnt** — bullet list
- **Good Patterns** — bullet list
- **User Profile Updates** — bullet list
- **Factual Discoveries** — bullet list
- **Sessions Covered** — list of `date · topic`
- **Memories Created** — clickable UUIDs (navigate to Detail tab)

**Cron Activity** (secondary, collapsible):

- Mirrors the old Runs tab content (run_log.jsonl)
- Label: "Legacy cron run history"
- Collapsed by default

### New REST Endpoints

| Method | Endpoint                | Purpose                              |
| ------ | ----------------------- | ------------------------------------ |
| `GET`  | `/api/reflections`      | List all reflections, newest first   |
| `GET`  | `/api/reflections/{id}` | Single reflection + sessions covered |

---

## File Inventory

| File                                                | Change                                            |
| --------------------------------------------------- | ------------------------------------------------- |
| `src/lorekeeper/models.py`                          | Add `Reflection`, `SessionRecord` Pydantic models |
| `src/lorekeeper/services/link_store.py`             | Add 2 tables, CRUD methods, startup migration     |
| `src/lorekeeper/services/orchestrator.py`           | Add `submit_reflection()`                         |
| `src/lorekeeper/handlers.py`                        | Add `handle_reflect()`                            |
| `src/lorekeeper/server.py`                          | Register `lore_reflect` tool                      |
| `src/lorekeeper/dashboard/app.py`                   | Add 2 REST endpoints                              |
| `src/lorekeeper/dashboard/static/index.html`        | Replace Runs tab with Reflections tab             |
| `src/lorekeeper/dashboard/static/js/reflections.js` | New module (reflections + collapsed runs)         |
| `src/lorekeeper/dashboard/static/js/app.js`         | Register reflections module, deregister runs      |
| `prompt/skills/reflect/SKILL.md`                    | Add `lore_reflect` call as final step             |

---

## Build Order

1. Models — `Reflection`, `SessionRecord`
2. `link_store.py` — tables + CRUD + startup migration
3. `orchestrator.py` — `submit_reflection()`
4. `handlers.py` + `server.py` — MCP tool
5. `dashboard/app.py` — REST endpoints
6. Dashboard UI — `index.html` + `reflections.js` + `app.js`
7. Skill update — `prompt/skills/reflect/SKILL.md`
