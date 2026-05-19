# Lorekeeper

Personal AI memory MCP server. Stores facts, decisions, and domain knowledge so AI agents can recall them across sessions.

Built with Python + [Mem0](https://github.com/mem0ai/mem0) + ChromaDB. Exposes five MCP tools over stdio: `lore_search`, `lore_insert`, `lore_update`, `lore_reflect`, `lore_processed_sessions`.

**Features**

- **Hybrid search** — combines semantic vector similarity (Mem0 + ChromaDB) with BM25 keyword search, re-ranked by a weighted formula
- **Relevance feedback** — agents report which memories were useful; scores drift up or down over time, unreliable memories are soft-deleted
- **Duplicate detection** — new inserts are checked against existing memories; blocked when similarity exceeds threshold (overridable with `force`)
- **Memory linking** — memories connect via typed, scored relationships forming a lightweight knowledge graph
- **Dashboard** — local web UI to browse, search, edit, and delete memories and links
- **Backup / restore** — export all memories + links to a portable JSON file; import with dedup preview

---

## How it works

Two stores work together:

| Store | What it holds |
|-------|--------------|
| **Mem0 + ChromaDB** | Vector embeddings (384-dim `all-MiniLM-L6-v2`) for semantic search |
| **SQLite sidecar** | Memory metadata (score, confidence, usage count, soft-deleted flag) + link rows + reflection records + session records + BM25 index source |

Every memory has a canonical `lore_id` UUID that lives in Mem0's metadata. The SQLite DB is the source of truth for everything else — scores, links, deletion state.

### Hybrid search scoring

Results are ranked by a weighted combination:

```
combined = 0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm
```

Semantic candidates come from Mem0 (top 200). Keyword candidates come from BM25. Both pools are unioned and re-ranked.

### Quality signals

Each time you call `lore_update` with feedback:

- `useful=true` → score bumped up, weighted by confidence
- `useful=false` → score bumped down
- `useful=false` + `confidence ≤ 2` → memory soft-deleted (never returned again)

Confidence is stored as a running EMA over the last 20 ratings.

---

## MCP tools

### `lore_search`

```json
{
  "query": "checkout payment flow",
  "limit": 10,
  "min_score": 0.1,
  "include_links": true,
  "include_deleted": false
}
```

Returns ranked memories with relevance scores and linked memories.

### `lore_insert`

```json
{
  "memories": [
    {
      "title": "Mutable default args in Python",
      "description": "def f(x=[]) shares the list across all calls — use None instead.",
      "content": "..."
    }
  ],
  "links": [
    {
      "source_memory_id": "<uuid>",
      "target_memory_id": "<uuid>",
      "relation_type": "related_to",
      "reason": "Both about Python gotchas"
    }
  ],
  "force": false
}
```

Duplicate detection runs automatically. Before inserting, the server computes a dedup score (`0.6·semantic + 0.4·keyword`). If it meets or exceeds `LORE_DUPLICATE_THRESHOLD` (default 0.85), the insert is blocked and the existing memory is returned. Use `force: true` to override.

### `lore_update`

```json
{
  "memory_feedback": [
    { "id": "<uuid>", "useful": true, "confidence": 8 }
  ],
  "link_feedback": [
    { "id": "<uuid>", "useful": false }
  ]
}
```

Drives the quality signal loop. Call this after every `lore_search` to keep scores calibrated.

### `lore_reflect`

```json
{
  "session_id": "uuid1",
  "summary": "Implemented reflect integration; extracted 3 lessons.",
  "session_date": "2026-05-19",
  "topic": "reflect-integration",
  "task_type": "build",
  "what_was_done": "Built the reflect integration...",
  "decisions": "- Used single-session submit for context efficiency",
  "lessons_learnt": ["Don't skip dedup check before inserting"],
  "good_patterns": ["Parallelise independent API calls"],
  "memory_ids": ["uuid-a", "uuid-b"]
}
```

Marks one session as processed and stores its content in the dashboard Sessions tab. Call once per session — reflect, submit, then move to the next. Returns `{ reflection_id, session_id, created_at }`.

---

## Setup

**Requirements**: Python 3.11+, [`uv`](https://github.com/astral-sh/uv)

```bash
git clone <repo-url> lorekeeper
cd lorekeeper
bash scripts/setup.sh
```

The script installs deps, creates `~/.lorekeeper/`, registers the MCP server in `~/.claude/settings.json`, and installs the three Claude Code skills. Restart Claude Code after running it.

To migrate data from a v1 `memories.json`:

```bash
V1_JSON=/path/to/memories.json bash scripts/setup.sh
```

**Manual install** (if you prefer step by step):

```bash
uv sync --extra dashboard   # install dependencies
uv run lorekeeper           # run the MCP server (stdio transport)
```

Data is stored at `~/.lorekeeper/` by default:

```
~/.lorekeeper/
├── chroma/          # ChromaDB vector store
└── lorekeeper.db    # SQLite metadata + links
```

### Configuration

All settings use the `LORE_` prefix and can be set via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LORE_DATA_DIR` | `~/.lorekeeper` | Storage directory |
| `LORE_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `LORE_DUPLICATE_THRESHOLD` | `0.85` | Similarity above which inserts are blocked |
| `LORE_W_SEMANTIC` | `0.45` | Semantic score weight |
| `LORE_W_KEYWORD` | `0.30` | BM25 keyword score weight |
| `LORE_W_MEMORY` | `0.15` | Memory score weight |
| `LORE_W_USAGE` | `0.10` | Usage frequency weight |
| `LORE_SCORE_BUMP_UP` | `0.1` | Score increase on positive feedback |
| `LORE_SCORE_BUMP_DOWN` | `0.05` | Score decrease on negative feedback |
| `LORE_SOFT_DELETE_CONFIDENCE_THRESHOLD` | `2` | Confidence ≤ this + `useful=false` triggers soft-delete |
| `LORE_CONFIDENCE_WINDOW_SIZE` | `20` | Rolling window size for confidence EMA |
| `LORE_DASH_PORT` | `7777` | Dashboard HTTP port |
| `LORE_DASH_RELOAD` | `1` | Dashboard hot-reload (`0` to disable) |

---

## Claude Code integration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "lorekeeper": {
      "command": "uv",
      "args": ["--directory", "/path/to/lorekeeper", "run", "lorekeeper"],
      "env": {}
    }
  }
}
```

Then in any project's `CLAUDE.md`, instruct the agent to check Lorekeeper at the start of every task:

```markdown
At the start of any task, run `lore_search` with the task topic before writing code or making decisions.
After the task, save new discoveries with `lore_insert` and `lore_update`.
```

---

## Distribution

### Share as a git repo (recommended)

Clone and run the setup script — covers everything in one step:

```bash
git clone <repo-url> lorekeeper
cd lorekeeper
bash scripts/setup.sh
```

### Build a wheel

To distribute without requiring a git clone (e.g. to teammates):

```bash
uv build                            # produces dist/lorekeeper-2.0.0-py3-none-any.whl
```

Recipient installs the wheel and then runs setup for MCP registration + skills:

```bash
pip install lorekeeper-2.0.0-py3-none-any.whl
# then in the cloned repo:
bash scripts/setup.sh
```

Or install globally as a `uv` tool so `lorekeeper` is on PATH without `uv run`:

```bash
uv tool install ./dist/lorekeeper-2.0.0-py3-none-any.whl
```

Then update `~/.claude/settings.json` to use the tool directly instead of `uv run`:

```json
{
  "mcpServers": {
    "lorekeeper": {
      "command": "lorekeeper",
      "args": [],
      "env": { "LORE_DATA_DIR": "~/.lorekeeper" }
    }
  }
}
```

### What `setup.sh` does

| Step | Action |
|------|--------|
| 1 | Checks Python 3.11+ and `uv` are available |
| 2 | Runs `uv sync --extra dashboard` |
| 3 | Creates `$LORE_DATA_DIR` (default `~/.lorekeeper`) |
| 4 | Adds `lorekeeper` entry to `~/.claude/settings.json` |
| 5 | Copies `assets/skills/lorekeeper-*/` to `~/.claude/skills/` |
| 6 | Migrates from v1 `memories.json` if `V1_JSON` env var is set |

The script is idempotent — safe to re-run after updates.

---

## Skills

Three Claude Code skills ship in `assets/skills/` and are installed by `setup.sh`:

| Skill | Purpose |
|-------|---------|
| `lorekeeper-search` | Search memories with mandatory relevance feedback after every result set |
| `lorekeeper-memorize` | Proactively capture facts, search for related memories, insert, and link |
| `lorekeeper-reconcile` | Verify memories against source materials, update scores, soft-delete incorrect facts |

Skills are installed to `~/.claude/skills/` and work with any project that has the MCP server configured.

---

## Dashboard

A local read/write web UI for browsing and managing your memory store. Requires the `dashboard` extras:

```bash
uv sync --extra dashboard
uv run lorekeeper-dashboard
# → http://127.0.0.1:7777  (override with LORE_DASH_PORT)
```

Hot-reload is **on by default** — Python file changes restart the server automatically. Disable with `LORE_DASH_RELOAD=0`. HTML edits are instant without restart (served fresh from disk on every request, just refresh the browser).

The UI has seven tabs:

| Tab | Purpose |
|-----|---------|
| **Memories** | Sortable table with live filter (type `/` to focus, `Esc` to clear). Shows title + description subtitle, score badge, confidence, usage count, dates. Score stats (high/mid/low) in the toolbar. Click a row to open it in Detail. |
| **Detail** | Edit a memory's title/description/content/score, soft-delete/restore, hard-delete, manage links. |
| **Links** | Flat sortable table of all links with source → relation → target. Click titles to navigate to that memory. |
| **Query** | Large text box for ad-hoc search. Shows combined/semantic/keyword scores and a relevance bar per result. |
| **Sessions** | All processed Claude sessions. Sidebar has session ID search (substring) and task-type filter chips. Date column is sortable (click header). Each row shows the review timestamp in UTC+8 with a relative time label below (e.g. "2h ago"), truncated session ID (hover for full UUID), topic, task type, and a summary of what was done. Stub sessions (no content) are hidden by default — toggle with the **Hide stubs** button. Click a row to expand full content: what was done, decisions, lessons learnt, good patterns, user profile observations, and discoveries. |
| **Config** | Live settings editor for search weights, quality signals, and limits. Changes apply immediately but reset on restart; use `LORE_*` env vars to persist. |
| **Backup** | Export all memories + links as a JSON file. Import a backup with dedup preview (shows counts and a scrollable list of each new memory/link to be inserted) before confirming. |

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/memories` | List all memories (`?include_deleted=true` to include soft-deleted) |
| `GET` | `/api/memories/{id}` | Get a single memory with its links |
| `PATCH` | `/api/memories/{id}` | Update fields: `title`, `description`, `content`, `score`, `soft_deleted` |
| `DELETE` | `/api/memories/{id}` | Hard-delete a memory (cascades to links) |
| `GET` | `/api/links` | List all links with source/target titles (`?include_deleted=true`) |
| `POST` | `/api/links` | Create a link between two memories |
| `DELETE` | `/api/links/{id}` | Delete a link |
| `POST` | `/api/search` | Search with `{ query, limit, min_score }` |
| `GET` | `/api/sessions` | Sessions with content (`?with_content=false` to include all) |
| `GET` | `/api/sessions/{id}` | Single session with its reflection metadata |
| `GET` | `/api/reflections` | List all reflection run records, newest first |
| `GET` | `/api/reflections/{id}` | Single reflection with sessions covered |
| `GET` | `/api/export` | Download all memories + links as JSON (`?include_deleted=true` to include soft-deleted) |
| `POST` | `/api/import/preview` | Dry-run import: returns counts + full list of memories/links that would be inserted, without writing |
| `POST` | `/api/import/confirm` | Actual import: inserts new memories + links, skips IDs already present |

The dashboard connects to the same SQLite + ChromaDB store as the MCP server. Both can technically run at the same time (SQLite WAL mode supports concurrent readers/writers), but the in-memory BM25 index in each process won't see the other's inserts until restart.

---

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check src tests

# Type check
uv run mypy src

# Optional: run the dashboard (requires dashboard extras)
uv sync --extra dashboard
uv run lorekeeper-dashboard
```

---

## Project layout

```
src/lorekeeper/
├── __main__.py              # Entrypoint — init_service() + mcp.run(stdio)
├── server.py                # FastMCP tool definitions (lore_search/insert/update/reflect/processed_sessions)
├── handlers.py              # Request handling + response serialisation
├── config.py                # Settings (pydantic-settings, LORE_ prefix)
├── models.py                # Memory, MemoryLink, Reflection, SessionRecord Pydantic models
├── dashboard/               # Optional web UI (FastAPI + uvicorn)
├── logging_setup.py         # structlog config (stderr only — stdout is MCP protocol)
└── services/
    ├── orchestrator.py      # MemoryService — coordinates all sub-services
    ├── memory_engine.py     # Mem0 + ChromaDB wrapper, semantic scale probe
    ├── link_store.py        # SQLite — memory rows, links, reflections, sessions, BM25 source
    ├── keyword_index.py     # BM25 index (rank-bm25)
    ├── search.py            # Hybrid ranking, SearchResult type
    ├── dedup.py             # Duplicate detection
    └── feedback.py          # Score delta, confidence EMA, soft-delete logic
```

---

## Agentic loop

This repo also demonstrates a self-improving agent pattern. Every session leaves a log in `loop/sessions/`. `/reflect` processes those transcripts, extracts learnings into Lorekeeper, and calls `lore_reflect` to mark sessions as processed — visible in the dashboard's **Sessions** tab.

```
/reflect (manual or scheduled)
    ↓
Checks sessions table to find unprocessed Claude transcripts
    ↓
Writes session logs to loop/sessions/YYYY-MM-DD-{topic}.md
    ↓
Updates Lorekeeper: lore_insert/update + feedback on existing memories
    ↓
Calls lore_reflect once per session → marks session processed, stores content
    ↓
Dashboard Sessions tab shows all processed sessions with full content
```

To schedule daily runs via crontab (runs at 09:30):

```bash
(crontab -l 2>/dev/null; echo "30 9 * * * LORE_RECAP_TRIGGER=cron /Users/jessin.donnyson/.local/bin/claude --print '/recap-sessions' >> /tmp/recap-sessions.log 2>&1") | crontab -
```
