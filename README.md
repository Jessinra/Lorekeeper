# Lorekeeper

Personal AI memory MCP server. Stores facts, decisions, and domain knowledge so AI agents can recall them across sessions.

Built with Python + [Mem0](https://github.com/mem0ai/mem0) + ChromaDB (or LanceDB). Exposes six MCP tools over stdio: `lore_search`, `lore_remember`, `lore_insert`, `lore_update`, `lore_reflect`, `lore_processed_sessions`.

**Features**

- **Hybrid search** — combines semantic vector similarity (LanceDB or ChromaDB) with BM25 keyword search, re-ranked by a weighted formula
- **Relevance feedback** — agents report which memories were useful; scores drift up or down over time, unreliable memories are soft-deleted
- **Duplicate detection** — new inserts are checked against existing memories; blocked when similarity exceeds threshold (overridable with `force`)
- **Memory linking** — memories connect via typed, scored relationships forming a lightweight knowledge graph
- **Dashboard** — local web UI to browse, search, edit, and delete memories and links
- **Backup / restore** — export all memories + links to a portable JSON file; import with dedup preview

---

## How it works

Two stores work together:

| Store                             | What it holds                                                                                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **LanceDB (default) or ChromaDB** | Vector embeddings (384-dim `all-MiniLM-L6-v2`) for semantic search. Set `LORE_VECTOR_STORE=chroma` to switch back to Chroma.               |
| **SQLite sidecar**                | Memory metadata (score, confidence, usage count, soft-deleted flag) + link rows + reflection records + session records + BM25 index source |

Every memory has a canonical `lore_id` UUID that lives in Mem0's metadata. The SQLite DB is the source of truth for everything else — scores, links, deletion state.

### Hybrid search scoring

Results are ranked by a weighted combination:

```
combined = 0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm
final    = combined × decay
```

Where `decay = e^(-λ · days_since_last_used)` applies time-decay so stale memories rank lower.  
`λ` defaults to `0.0077` (~90-day half-life) and is configurable via `LORE_DECAY_LAMBDA`. Set to `0` to disable decay entirely.  
`last_used` is updated each time a memory is retrieved; if not set, `created_at` is used as the reference date.  
The `decay_factor` is exposed on every search result for debugging.

`min_score` filtering is applied to `combined` (before decay) so that relevance, not age, gates inclusion.

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
  "min_score": 0.1,
  "include_links": true,
  "include_deleted": false,
  "refine_from": null,
  "format": "full",
  "ids": null
}
```

Returns ranked memories with relevance scores and linked memories.

Two search modes:

**Query mode** (default) — runs the hybrid semantic + BM25 pipeline. Parameters:

- `query` (required unless `ids` is set): search text
- `min_score` (default `0.1`): minimum `combined_score` threshold
- `refine_from`: pass a list of `lore_id` strings from a previous search result to re-rank only within that candidate set using a new query. Unknown IDs are silently ignored. Max 200 IDs (configurable via `LORE_MAX_REFINE_FROM_IDS`)
- `format`: `"full"` (default) returns complete memory objects with relevance scores; `"title"` returns compact `{id, title, score}` dicts for lower token cost

**ID lookup mode** — when `ids` is set, skips the vector/BM25 pipeline entirely and fetches those specific `lore_id`s directly from SQL. Unknown IDs are silently ignored. `query` is ignored in this path. Max 50 IDs (configurable via `LORE_MAX_SEARCH_IDS`). Pair `ids` with `format='title'` for a two-step workflow: list titles first, then fetch full objects for specific IDs.

Other params: `limit` (max results, defaults to `LORE_SEARCH_LIMIT`), `include_links` (default `true`; forced off in `format='title'` mode), `include_deleted` (default `false`).

### `lore_insert`

```json
{
  "memories": [
    {
      "title": "Mutable default args in Python",
      "description": "def f(x=[]) shares the list across all calls — use None instead.",
      "content": "..."
    },
    {
      "title": "Token refresh interval",
      "content": "Access tokens expire after 1h.",
      "links": [
        {
          "target_memory_id": "<target-uuid>",
          "relation_type": "related_to",
          "reason": "part of OAuth flow"
        }
      ]
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

Each memory dict may include:

- `title` (required): short unique label
- `content` (optional): the full text to store
- `description` (optional): brief summary
- `score` (optional, default 5.0): initial quality score 0–10
- `links` (optional): inline links to create after insert. Each link: `{target_memory_id (required), relation_type (required), reason? (optional)}`

Top-level `links` (linking existing memories to each other) and per-memory inline `links` can be used together in a single call.

Duplicate detection runs automatically. Before inserting, the server computes a dedup score (`0.6·semantic + 0.4·keyword`). If it meets or exceeds `LORE_DUPLICATE_THRESHOLD` (default 0.85), the insert is blocked and the existing memory is returned. Use `force: true` to override.

### `lore_remember`

```json
{
  "thought": "Hybrid search formula: 0.45 semantic + 0.30 keyword + 0.15 score + 0.10 usage"
}
```

Fast one-shot memory insert — zero friction. Pass a thought as a single string; the server auto-extracts the title (first ~80 chars, sentence boundary), stores the full content verbatim with a default score of 7.0, and auto-links to the nearest semantic neighbor if similarity ≥ 0.75. Returns `{id, title, linked_to: {id, score} | null}`. Uses the same dedup pipeline as `lore_insert` — exact title matches are definitive duplicates.

Use this for quick capture. Use `lore_insert` when you need explicit titles, descriptions, scores, or manual links.

### `lore_update`

```json
{
  "memory_feedback": [{ "id": "<uuid>", "useful": true, "confidence": 8 }],
  "link_feedback": [{ "id": "<uuid>", "useful": false }]
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
  "factual_discoveries": ["BM25 rebuild costs ~10ms at 5k memories"],
  "memory_ids": ["uuid-a", "uuid-b"],
  "auto_insert": true
}
```

Marks one session as processed and stores its content in the dashboard Sessions tab. Call once per session — reflect, submit, then move to the next.

**Auto-insert (default `auto_insert=true`):** Each item in `factual_discoveries` and `lessons_learnt` is automatically inserted as a standalone searchable memory. Discoveries get score 7.0, lessons get score 8.0. Duplicate-guarded — items already in the store are silently skipped (existing ID returned). Pass `auto_insert=false` to store only in the reflection record without creating memories.

Returns:
```json
{
  "reflection_id": "...",
  "session_id": "...",
  "created_at": "...",
  "memories_created": [
    {"id": "m-1", "title": "BM25 rebuild costs ~10ms...", "relation": "discovered_in"},
    {"id": "m-2", "title": "Don't skip dedup check...", "relation": "learned_in"}
  ]
}
```

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
├── lancedb/         # LanceDB vector store (default)
├── chroma/          # ChromaDB vector store (when LORE_VECTOR_STORE=chroma)
└── lorekeeper.db    # SQLite metadata + links
```

> **Note**: LanceDB and Chroma stores are independent. Switching between them won't share embeddings — re-seed with `uv run python scripts/seed_lancedb.py` after switching. Existing data in the inactive store is never modified.

### Configuration

All settings use the `LORE_` prefix and can be set via environment variables:

| Variable                                | Default                                  | Description                                                                                             |
| --------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `LORE_VECTOR_STORE`                     | `lancedb`                                | Vector store backend: `lancedb` (default) or `chroma`                                                   |
| `LORE_DATA_DIR`                         | `~/.lorekeeper`                          | Storage directory                                                                                       |
| `LORE_NAMESPACE`                        | `shared`                                 | Agent write namespace. Writes are tagged with this value; reads return memories in `[namespace, "shared"]`. Set automatically by `setup.sh` for all Hermes agents (`hermes_main` gets `"shared"`, profiles get their directory name). |
| `LORE_EMBEDDING_MODEL`                  | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model                                                                                         |
| `LORE_DUPLICATE_THRESHOLD`              | `0.85`                                   | Similarity above which inserts are blocked                                                              |
| `LORE_W_SEMANTIC`                       | `0.45`                                   | Semantic score weight                                                                                   |
| `LORE_W_KEYWORD`                        | `0.30`                                   | BM25 keyword score weight                                                                               |
| `LORE_W_MEMORY`                         | `0.15`                                   | Memory score weight                                                                                     |
| `LORE_W_USAGE`                          | `0.10`                                   | Usage frequency weight                                                                                  |
| `LORE_SCORE_BUMP_UP`                    | `0.1`                                    | Score increase on positive feedback                                                                     |
| `LORE_SCORE_BUMP_DOWN`                  | `0.05`                                   | Score decrease on negative feedback                                                                     |
| `LORE_SOFT_DELETE_CONFIDENCE_THRESHOLD` | `2`                                      | Confidence ≤ this + `useful=false` triggers soft-delete                                                 |
| `LORE_CONFIDENCE_WINDOW_SIZE`           | `20`                                     | Rolling window size for confidence EMA                                                                  |
| `LORE_SEARCH_LIMIT`                     | `5`                                      | Default number of memories returned by `lore_search`                                                    |
| `LORE_MAX_SEARCH_IDS`                  | `50`                                     | Max IDs in `lore_search(ids=[...])` lookup — enforced at handler layer                                  |
| `LORE_MAX_REFINE_FROM_IDS`             | `200`                                    | Max IDs in `lore_search(refine_from=[...])` — enforced at handler layer                                 |
| `LORE_MAX_LINKS_PER_MEMORY`             | `5`                                      | Limit links returned per memory in search results                                                       |
| `LORE_SCORE_MIN`                        | `0.0`                                    | Minimum allowed memory score                                                                            |
| `LORE_SCORE_MAX`                        | `10.0`                                   | Maximum allowed memory score                                                                            |
| `LORE_NEW_MEMORY_DEFAULT_SCORE`         | `5.0`                                    | Default score for new memories                                                                          |
| `LORE_USAGE_NORMALISATION_CAP`          | `100`                                    | Cap for log-normalising `usage_count` in hybrid scoring                                                 |
| `LORE_DECAY_LAMBDA`                     | `0.0077`                                 | Time-decay λ for scoring (~90-day half-life; set to 0 to disable)                                       |
| `LORE_AUTO_LINK_ENABLED`                | `true`                                   | Enable automatic linking of semantically similar memories on insert (set `false` to disable)            |
| `LORE_AUTO_LINK_K`                      | `5`                                      | Candidate count for auto-link vector search (ε-NN + top-k hybrid)                                       |
| `LORE_AUTO_LINK_THRESHOLD`              | `0.85`                                   | Minimum cosine similarity to auto-link; 0.85–0.95 = strong same-topic, 0.75–0.85 = related but distinct |
| `LORE_DASH_PORT`                        | `7777`                                   | Dashboard HTTP port                                                                                     |
| `LORE_DASH_RELOAD`                      | `1`                                      | Dashboard hot-reload (`0` to disable)                                                                   |

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

| Step | Action                                                                                                                  |
| ---- | ----------------------------------------------------------------------------------------------------------------------- |
| 1    | Checks Python 3.11+ and `uv` are available                                                                              |
| 2    | Runs `uv sync --extra dashboard`                                                                                        |
| 3    | Creates `$LORE_DATA_DIR` (default `~/.lorekeeper`)                                                                      |
| 4    | Installs git hooks (lint + tests enforced on commit)                                                                    |
| 5    | Scans for Hermes (main + profiles), Claude Code, and Cursor                                                             |
| 6    | Asks confirmation, then for each detected agent: injects MCP config, injects Lorekeeper prompt section, installs skills |
| 7    | Migrates from v1 `memories.json` if `V1_JSON` env var is set                                                            |

The script is idempotent — safe to re-run after updates. Version-stamped injections are skipped when already up to date, and overwritten cleanly when the version differs.

#### Agent detection

`setup.sh` auto-detects agents by checking for their config directories:

| Agent             | Detected by                            |
| ----------------- | -------------------------------------- |
| Hermes (main)     | `~/.hermes/` directory                 |
| Hermes (profiles) | `~/.hermes/profiles/*/` subdirectories |
| Claude Code       | `~/.claude/` directory                 |
| Cursor            | `~/.cursor/` directory                 |

For **MCP injection**, the script appends a `lorekeeper` entry to each agent's config (YAML for Hermes, JSON for Claude Code/Cursor). Already-present entries are left unchanged.

For **prompt injection**, the script injects a `## Lorekeeper` section into the agent's prompt file (`soul.md` for Hermes; `CLAUDE.md` / `.cursorrules` / `AGENTS.md` in the current directory for others). Re-running updates the section if the version stamp differs.

For **skills**, `assets/skills/` is copied to each agent's skills directory. Dev skills (`.hermes/skills/`) are symlinked to `~/.hermes/skills/` for Hermes only.

The single source of truth for the prompt content and version is `assets/prompts/lorekeeper-agent-prompt.md`.

---

## Skills

Four skills ship in `assets/skills/` and are installed by `setup.sh` to all detected agents (Hermes, Claude Code, Cursor):

| Skill                  | Purpose                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------ |
| `lorekeeper-protocol`  | Full session protocol — when and how to call all Lorekeeper tools                    |
| `lorekeeper-search`    | Search memories with mandatory relevance feedback after every result set             |
| `lorekeeper-memorize`  | Proactively capture facts, search for related memories, insert, and link             |
| `lorekeeper-reconcile` | Verify memories against source materials, update scores, soft-delete incorrect facts |

Skills are installed to `~/.hermes/skills/`, `~/.claude/skills/`, or `~/.cursor/skills/` depending on which agents are detected. Version-stamped — `setup.sh` skips re-install when already up to date.

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

| Tab          | Purpose                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Memories** | Sortable table with live filter (type `/` to focus, `Esc` to clear). Shows title + description subtitle, score badge, confidence, usage count, dates. Score stats (high/mid/low) in the toolbar. Click a row to open it in Detail.                                                                                                                                                                                                                                                                                                                                           |
| **Detail**   | Edit a memory's title/description/content/score, soft-delete/restore, hard-delete, manage links.                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **Links**    | Flat sortable table of all links with source → relation → target. Click titles to navigate to that memory.                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **Query**    | Large text box for ad-hoc search. Shows combined/semantic/keyword scores and a relevance bar per result.                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Sessions** | All processed Claude sessions. Sidebar has session ID search (substring) and task-type filter chips. Date column is sortable (click header). Each row shows the review timestamp in UTC+8 with a relative time label below (e.g. "2h ago"), truncated session ID (hover for full UUID), topic, task type, and a summary of what was done. Stub sessions (no content) are hidden by default — toggle with the **Hide stubs** button. Click a row to expand full content: what was done, decisions, lessons learnt, good patterns, user profile observations, and discoveries. |
| **Config**   | Live settings editor for search weights, quality signals, and limits (search result count, links per memory). Changes apply immediately but reset on restart; use `LORE_*` env vars to persist.                                                                                                                                                                                                                                                                                                                                                                              |
| **Backup**   | Export all memories + links as a JSON file. Import a backup with dedup preview (shows counts and a scrollable list of each new memory/link to be inserted) before confirming.                                                                                                                                                                                                                                                                                                                                                                                                |

### API endpoints

| Method   | Path                    | Description                                                                                          |
| -------- | ----------------------- | ---------------------------------------------------------------------------------------------------- |
| `GET`    | `/api/memories`         | List all memories (`?include_deleted=true` to include soft-deleted)                                  |
| `GET`    | `/api/memories/{id}`    | Get a single memory with its links                                                                   |
| `PATCH`  | `/api/memories/{id}`    | Update fields: `title`, `description`, `content`, `score`, `soft_deleted`                            |
| `DELETE` | `/api/memories/{id}`    | Hard-delete a memory (cascades to links)                                                             |
| `GET`    | `/api/links`            | List all links with source/target titles (`?include_deleted=true`)                                   |
| `POST`   | `/api/links`            | Create a link between two memories                                                                   |
| `DELETE` | `/api/links/{id}`       | Delete a link                                                                                        |
| `POST`   | `/api/search`           | Search with `{ query, limit, min_score }`                                                            |
| `GET`    | `/api/sessions`         | Sessions with content (`?with_content=false` to include all)                                         |
| `GET`    | `/api/sessions/{id}`    | Single session with its reflection metadata                                                          |
| `GET`    | `/api/reflections`      | List all reflection run records, newest first                                                        |
| `GET`    | `/api/reflections/{id}` | Single reflection with sessions covered                                                              |
| `GET`    | `/api/export`           | Download all memories + links as JSON (`?include_deleted=true` to include soft-deleted)              |
| `POST`   | `/api/import/preview`   | Dry-run import: returns counts + full list of memories/links that would be inserted, without writing |
| `POST`   | `/api/import/confirm`   | Actual import: inserts new memories + links, skips IDs already present                               |

The dashboard connects to the same SQLite + vector store (LanceDB or ChromaDB) as the MCP server. Both can technically run at the same time (SQLite WAL mode supports concurrent readers/writers), but the in-memory BM25 index in each process won't see the other's inserts until restart.

---

## Development

Run once per clone to install deps, git hooks, and skill symlinks:

```bash
bash scripts/setup.sh
```

**Prerequisites**: `uv`, `node` (for Biome JS linter)

```bash
# Tests
uv run pytest
uv run pytest tests/ -x -q    # fail-fast

# Lint — Python (also runs in pre-commit hook)
uv run ruff check src tests
uv run ruff check src tests --fix

# Lint — JS dashboard (also runs in pre-commit hook)
npx @biomejs/biome check src/lorekeeper/dashboard/static/js/
npx @biomejs/biome check src/lorekeeper/dashboard/static/js/ --write

# Type check — run before pushing (not in pre-commit hook, too slow)
uv run mypy src

# Optional: run the dashboard (requires dashboard extras)
uv sync --extra dashboard
uv run lorekeeper-dashboard
```

The pre-commit hook (installed by `setup.sh`) blocks commits on lint or test failures.  
Rule selection rationale: [`docs/linter-decisions.md`](docs/linter-decisions.md)

---

## PR Workflow

Always open PRs with **Copilot tagged as reviewer**:

```bash
gh pr create --base main --title "[LKPR-N] type: title" --body "..." --reviewer @copilot
```

Full details in `.hermes/skills/github-pr/SKILL.md`.

Reference: [Requesting a code review from Copilot](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)

---

## Commit Convention

All commits are enforced by a `commit-msg` git hook (installed via `bash scripts/setup.sh`).

**Author identity** (set once per clone):

```bash
git config --local user.name "Akane (PM)"   # or "Dev"
git config --local user.email "jessinra.kai@gmail.com"
```

**Commit title format**: `[LKPR-N] type: short title`

| Tag        | Use for                                                                |
| ---------- | ---------------------------------------------------------------------- |
| `[LKPR-N]` | Work tied to a specific ticket                                         |
| `[LKPR-0]` | Housekeeping — chore, backlog edits, status changes, skill/doc updates |

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

---

## Project layout

```
backlogs/
├── LKPR-N-<slug>.md       # Active tickets (proposal, backlog, in-progress, review)
├── done/                   # Completed tickets
└── TEMPLATE.md             # Ticket template
.hermes/
└── skills/                 # Agent skills (dev, pm, after-changes, ui-ux-pro-max, backlog-management)
docs/
└── plans/                   # Implementation plans (YYYY-MM-DD_HHMMSS-<slug>.md)
loop/
└── sessions/                # Agentic loop session logs (one per session)
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
    ├── engine_factory.py     # engine builder (build_engine) — returns MemoryEngine
    ├── lancedb_engine.py     # LanceDB backend (LanceDBEngine)
    ├── memory_engine.py      # Abstract MemoryEngine base + ChromaDB backend
    ├── link_store.py        # SQLite — memory rows, links, reflections, sessions, BM25 source (+ api_metrics)
    ├── keyword_index.py     # BM25 index (rank-bm25)
    ├── search.py            # Hybrid ranking, SearchResult type
    ├── dedup.py             # Duplicate detection
    └── feedback.py          # Score delta, confidence EMA, soft-delete logic
scripts/
├── lorekeeper-setup.sh      # Symlink repo skills → ~/.hermes/skills/
├── lorekeeper-backlog.sh    # Backlog viewer: group tickets by status, detect duplicates
└── setup.sh                 # User-facing setup script (install deps, register MCP, copy skills)
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
