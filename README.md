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

**Full reference with schemas and examples → see the [MCP tools](#) section below.**

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
