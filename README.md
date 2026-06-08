# Lorekeeper

> **Memory for AI agents that gets smarter the more you use it.**
>
> One command. No cloud. No config.
>
> ```bash
> pip install lorekeeper-mcp && lorekeeper
> ```
>
> Connect any MCP-compatible agent → it remembers across sessions.

![Lorekeeper dashboard — Memories tab](assets/dashboard-memories-tab.png)

---

## Why Lorekeeper

Every AI agent session starts blank. You re-explain context, re-state preferences, re-teach patterns. Files like `CLAUDE.md` or `.cursorrules` help, but they're manual, unscalable, and have no search or decay.

Lorekeeper gives your agent **persistent, self-improving memory** — install once, connect any agent, and it remembers everything. And unlike every other option, it gets _better_ with use:

```
Agent uses memories → rates relevance → scores adjust →
bad memories decay → good memories rise → agent trusts it more
```

**The feedback loop compounds.** A fresh install and a 3-month-old install are different products. The system learns what matters and quietly forgets what doesn't.

---

## Quick Start

3 minutes, zero configuration:

```bash
# 1. Install
pip install lorekeeper-mcp

# 2. Start
lorekeeper

# 3. Connect your agent
# Add this to ~/.claude/settings.json or your MCP config:
```

```json
{
  "mcpServers": {
    "lorekeeper": {
      "command": "lorekeeper",
      "args": [],
      "env": {}
    }
  }
}
```

Then ask your agent:

> _"Remember that I prefer `curl -vX GET` for debugging endpoints."_

It calls `lore_remember` → memory stored. Next session:

> _"What's my preferred debug command?"_

It calls `lore_search` → memory retrieved. ✅

**Full walkthrough → [docs/quickstart.md](docs/quickstart.md)**

---

## Features

| What                    | How                                                                                                                           |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Hybrid search**       | Semantic vectors + BM25 keyword + time-decay + usage frequency + memory score — all ranked by a weighted formula              |
| **Self-improving**      | `lore_update` feedback adjusts scores. Bad memories fade (<2 confidence + not useful → soft-delete). Good ones rise.          |
| **Auto-linking**        | New memories are automatically linked to their closest semantic neighbor. A lightweight knowledge graph forms without effort. |
| **Duplicate detection** | New inserts are checked against existing memories. Near-identical content is blocked (override with `force=true`).            |
| **Dashboard**           | Full web UI — browse, search, edit, delete. Seven tabs including backup/restore with dedup preview.                           |
| **Universal MCP**       | Works with Claude Code, Cursor, Hermes, Copilot, OpenCode — any MCP-compatible agent.                                         |
| **Local-first**         | Your data stays on your machine. SQLite + LanceDB (or ChromaDB). No cloud dependency, no API keys.                            |
| **Namespaces**          | Multiple agents share one store with isolated namespaces. Writes go to your namespace; reads include the shared pool.         |
| **Reflection**          | Agents auto-extract learnings from sessions. Discoveries and lessons become searchable memories.                              |

---

## Who It's For

**You, if you use:**

- Claude Code and want it to remember project context between sessions
- Cursor and want persistent agent memory
- Hermes, OpenCode, Codex CLI, Copilot CLI, or any MCP-compatible agent
- Multiple agents and want them to share knowledge

**Not for you yet, if:**

- You need team RBAC, audit logs, or SSO (coming post-beta)
- You're building a consumer AI app (we're agent-first, not API-first)
- You don't use AI coding agents (Lorekeeper is an MCP tool)

---

## How It Compares

|                     | File-based | Cloud services         | Docker servers   | Library (Mem0)         | agentmemory (Node) | **Lorekeeper**                          |
| ------------------- | ---------- | ---------------------- | ---------------- | ---------------------- | ------------------ | --------------------------------------- |
| **Setup**           | Built-in   | API key + cloud config | `docker compose` | Write integration code | `npx agentmemory`  | **`pip install`**                       |
| **Data**            | Local      | Cloud                  | Local            | Your call              | Local              | **Local**                               |
| **Search**          | grep       | Vector                 | Vector           | Vector                 | Hybrid             | **Hybrid + time-decay + usage + score** |
| **Self-improving**  | ❌         | ❌                     | ❌               | ❌                     | ❌                 | **✅ Quality loop**                     |
| **Knowledge graph** | ❌         | Paid                   | ❌               | Paid                   | ❌                 | **✅ Free auto-link**                   |
| **Dashboard**       | ❌         | ✅                     | ❌               | ❌                     | Viewer             | **✅ Full web UI**                      |
| **Dependencies**    | None       | ~300MB                 | ~2GB             | ~1.4GB                 | ~200MB             | **~1.4GB** (embeddings)                 |
| **Built by agents** | ❌         | ❌                     | ❌               | ❌                     | ❌                 | **✅ Dogfooded daily**                  |

> **Dependency note:** ~1.4GB is from the sentence-transformers embedding model (PyTorch). This is the same weight class as any local embedding solution. We're honest about it.

---

## MCP Tools

Lorekeeper exposes **8 MCP tools** covering the full memory lifecycle:

| Tool                      | Purpose                                                  |
| ------------------------- | -------------------------------------------------------- |
| `lore_search`             | Hybrid semantic + keyword search with relevance scores   |
| `lore_remember`           | Fast one-shot memory save (auto-titles, auto-links)      |
| `lore_insert`             | Bulk structured insert with custom scores and links      |
| `lore_update`             | Feedback loop — rate memories, drive quality             |
| `lore_forget`             | Soft-delete wrong or outdated memories                   |
| `lore_reflect`            | End-of-session: extract learnings, auto-save discoveries |
| `lore_processed_sessions` | Check which sessions are already processed               |
| `lore_recommend_links`    | Suggest candidate links between related memories         |

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

### `lore_forget`

```json
{
  "memory_ids": ["uuid1", "uuid2"],
  "reason": "hallucinated"
}
```

Immediately soft-deletes one or more memories. Use when a memory is wrong, duplicated, or outdated and you don't want it polluting future searches. The memory is excluded from `lore_search` results after this call.

`reason` must be one of: `duplicate`, `hallucinated`, `outdated`, `expired`, `unspecified`. Logged for auditability. Soft-delete is reversible at the DB level, but no undelete tool is exposed.

Returns `{ "forgotten": [...], "not_found": [...], "errors": [...] }`.

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

**Auto-insert (default `auto_insert=true`):** Each item in `factual_discoveries` and `lessons_learnt` is automatically inserted as a standalone searchable memory. Discoveries get score 7.0, lessons get score 8.0. Duplicate-guarded — items already in the store return the existing ID with `"status": "duplicate"`; newly inserted items have `"status": "inserted"`. Pass `auto_insert=false` to store only in the reflection record without creating memories.

**Idempotency:** If `session_id` was already processed, returns immediately with `"already_processed": true` and `"memories_created": []`. The `[]` reflects the current call only — the original call's auto-inserts are not reconstructed. Check `already_processed` to detect retries.

Returns:

```json
{
  "reflection_id": "...",
  "session_id": "...",
  "created_at": "...",
  "memories_created": [
    {
      "id": "m-1",
      "title": "BM25 rebuild costs ~10ms...",
      "relation": "discovered_in",
      "status": "inserted"
    },
    {
      "id": "m-2",
      "title": "Don't skip dedup check...",
      "relation": "learned_in",
      "status": "inserted"
    }
  ]
}
```

### `lore_processed_sessions`

No parameters. Returns all session IDs already marked as processed by `lore_reflect`.

```json
{}
```

Returns:

```json
{ "processed_session_ids": ["session-uuid-1", "session-uuid-2"] }
```

Use this to avoid re-processing sessions — check the list before calling `lore_reflect`.

### `lore_recommend_links`

```json
{
  "lore_id": "<uuid>",
  "top_k": 10
}
```

Suggests link candidates between a memory and related memories in the store. Single-stage scoring pipeline — semantic cosine, BM25, entity overlap, and temporal proximity combined into a weighted score. The agent evaluates the candidates and decides which links to create.

**Does NOT write any links.** Returns candidates for review — confirm by calling `lore_insert` with `links=[]`.

Parameters:

- `lore_id` (required): source memory to find candidates for
- `top_k` (optional, default from `LORE_LINK_TOP_M`): max candidates to return, overriding the default limit

Returns:

```json
{
  "candidates": [
    {
      "source_lore_id": "<uuid>",
      "target_lore_id": "<uuid>",
      "weighted_score": 0.65,
      "scores": {
        "cosine": 0.82,
        "bm25": 0.45,
        "entity": 0.0,
        "temporal": 0.0
      }
    }
  ],
  "count": 10,
  "source_lore_id": "<uuid>"
}
```

Per-signal `scores` lets the agent make its own judgment about which candidates are worth linking — no LLM call inside Lorekeeper.

---

## Dashboard

A local web UI to browse, search, edit, and manage your memory store.

```bash
lorekeeper-dashboard
# → http://127.0.0.1:7777
```

Seven tabs:

| Tab          | What it does                                                             |
| ------------ | ------------------------------------------------------------------------ |
| **Memories** | Sortable table with live filter — title, score, confidence, usage, dates |
| **Detail**   | Edit a memory's content, manage its links, soft-delete or hard-delete    |
| **Links**    | Browse the knowledge graph — source → relation → target                  |
| **Query**    | Ad-hoc semantic + keyword searches with per-result score breakdown       |
| **Sessions** | All processed agent sessions with extracted learnings                    |
| **Config**   | Live tuning of search weights, quality thresholds, limits                |
| **Backup**   | Export/import memories as JSON with dedup preview                        |

![Lorekeeper Query tab — hybrid search with scores](assets/dashboard-query-tab.png)

---

## Built by Agents, For Agents

Lorekeeper is developed using AI agents — Claude Code, Hermes, and our own agent team (Diana, Akane). The development cycle is itself a working demo:

```
agent builds feature → uses Lorekeeper to remember →
captures learnings → searches them next session →
builds the next feature better
```

Every tool schema, return type, and workflow is shaped by **actual agent usage** — not theoretical assumptions. The agentic loop documented in the repo isn't aspirational copy; it's how we work.

> **Why this matters:** A memory server built for agents by agents will always be more agent-friendly than one built by humans reading docs. Dogfooding is our design philosophy.

---

## Setup (Git clone)

If you prefer to clone the repo instead of pip install (e.g., for development):

```bash
git clone https://github.com/Jessinra/Lorekeeper.git
cd Lorekeeper
bash scripts/setup.sh
```

The setup script:

1. Installs dependencies with `uv sync`
2. Creates `~/.lorekeeper/` data directory
3. Installs git hooks (lint + tests enforced on commit)
4. Registers MCP config in detected agents (Claude Code, Cursor, Hermes)
5. Installs 5 agent skills for automatic memory workflows

**Prerequisites:** Python 3.11+, `uv` (or pip)

---

## Development

```bash
# Tests
uv run pytest

# Lint
uv run ruff check src tests

# Dashboard dev
uv sync --extra dashboard
uv run lorekeeper-dashboard

# Type check (before push)
uv run mypy src
```

Full development guide → `README.md` **Development** section (below).

---

## Project Layout

```
src/lorekeeper/
├── __main__.py          # Entrypoint — init_service() + mcp.run(stdio)
├── server.py            # FastMCP tool definitions (8 tools)
├── config.py            # Settings (pydantic-settings, LORE_ prefix)
├── models.py            # Pydantic models
├── dashboard/           # Web UI (FastAPI + uvicorn)
└── services/
    ├── orchestrator.py  # MemoryService — coordinates all sub-services
    ├── memory_engine.py # Vector store abstraction
    ├── lancedb_engine.py# LanceDB backend
    ├── chromadb_engine.py# ChromaDB backend
    ├── link_store.py    # SQLite — memories, links, reflections
    ├── keyword_index.py # BM25 index
    ├── search.py        # Hybrid ranking
    ├── dedup.py         # Duplicate detection
    ├── feedback.py      # Score delta, EMA, soft-delete
    ├── link_candidate.py# Link candidate pipeline
    └── relation_classifier.py # LLM-based relation classifier
```

---

## License

Apache-2.0 — see [LICENSE](LICENSE).

---

_Built by agents, for agents. [Read the strategy](docs/positioning-manifesto.md)._
