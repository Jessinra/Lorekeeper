<p align="center">
  <img src="docs/assets/logo.svg" width="180" alt="Lorekeeper">
</p>

<h1 align="center">Lorekeeper</h1>

<p align="center">
  <strong>Self-improving memory for AI agents. One command, no cloud, no config.</strong>
</p>

[![docs](https://img.shields.io/badge/docs-lorekeeper.dev-blue)](https://jessinra.github.io/Lorekeeper/)

> ```bash
> pip install lorekeeper-mcp && lorekeeper setup && lorekeeper
> ```
>
> Your agent remembers across sessions — and the memory gets **better, not just bigger.**
> Local. No API keys. No sign-up. **Free to run forever.**

---

## Why Lorekeeper

Every AI agent session starts blank. You re-explain context, re-state preferences, re-teach patterns — every single time.

Files like `CLAUDE.md` and `.cursorrules` help, but they're hand-maintained, can't search themselves, and grow stale. Cloud services work, but your session data leaves your machine and you're paying per API call. Libraries are powerful, but you're writing the integration yourself.

Lorekeeper is a different shape: **a local MCP server you `pip install` once.** It connects to your existing agents, stores memories in SQLite on your own disk, and starts improving with every session:

```
Agent uses a memory → rates it useful or not →
scores adjust automatically → weak memories decay →
strong memories surface more often → search gets sharper
```

A fresh install and a six-month-old install are **genuinely different products.** The longer you use it, the less noise you get — and the more your agents feel like they actually know your codebase.

---

## Quick Start

3 minutes, zero configuration:

```bash
# 1. Install
pip install lorekeeper-mcp

# 2. Configure your agents (auto-detects Hermes, Claude Code, Cursor)
lorekeeper setup

# 3. Start the MCP server
lorekeeper
```

`lorekeeper setup` scans for installed agents and injects the MCP entry, agent prompt, and bundled skills automatically. Use `--check` to preview without writing. Run `lorekeeper --help` or `lorekeeper --version` to verify the install.

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
| **Local-first**         | Your data stays on your machine. SQLite + LanceDB. No cloud dependency, no API keys.                                          |
| **Namespaces**          | Multiple agents share one store with isolated namespaces. Writes go to your namespace; reads include the shared pool.         |
| **Reflection**          | Agents auto-extract learnings from sessions. Discoveries and lessons become searchable memories.                              |

---

## Use Cases

### Staying in context across sessions

You set up your auth layer on Monday. Wednesday, a different agent starts fresh with no idea. With Lorekeeper, it already knows the middleware path, the token format, and which test covers the edge case — because you told it once.

```
"Remember that our JWT uses jose middleware in src/middleware/auth.ts
 and refresh tokens expire in 7 days."
→ lore_remember stores it
→ Every future session, on any agent: already in context
```

### One memory pool, multiple agents

Claude Code for review, Cursor for implementation, Hermes for planning — they shouldn't each start from zero. Lorekeeper namespaces let them share one store. One agent's discovery becomes every agent's knowledge.

```
→ Engineer agent notes a performance quirk in the search service
→ lore_remember stores it under the shared namespace
→ PM agent surfaces it during sprint planning
→ No briefing, no copy-paste
```

### Cross-session debugging

You fixed a subtle CORS bug three weeks ago and your agent helped. Neither of you remembers the details.

```
"What did we figure out about the CORS issue?"
→ lore_search returns the root cause, the fix, and the context around it
```

### Project onboarding

New repo, new agent session. Instead of re-explaining the architecture, you run a few `lore_remember` calls after the first session. The next session — and every agent after it — starts with the right foundation.

```
"Remember: the payment service requires X-Idempotency-Key on all POST requests."
→ Claude Code, Cursor, and Codex all read from the same store
```

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

There are great tools in this space — each makes different trade-offs. Here's where Lorekeeper sits:

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

Cloud services and Docker-based solutions are strong choices for teams or production apps. Lorekeeper is optimised for the other end: solo developers and agent workflows where **zero ops, zero cloud, and a self-improving store** matter most.

> **Dependency note:** ~1.4GB is from the sentence-transformers embedding model (PyTorch). This is the same weight class as any local embedding solution. We're honest about it.

---

## MCP Tools

Lorekeeper exposes **10 MCP tools** covering the full memory lifecycle:

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
| `lore_get_suggestions`    | List pending link suggestions from the sweep engine      |
| `lore_review_suggestion`  | Accept or reject one or more link suggestions (batch)    |

**Full API reference → [docs/api-reference.md](docs/api-reference.md)**

---

## Dashboard

A local web UI to browse, search, edit, and manage your memory store.

```bash
lorekeeper-dashboard
# → http://127.0.0.1:7777
```

Seven tabs:

| Tab             | What it does                                                                                       |
| --------------- | -------------------------------------------------------------------------------------------------- |
| **Memories**    | Sortable table with live filter — title, score, confidence, usage, dates                           |
| **Detail**      | Edit a memory's content, manage its links, soft-delete or hard-delete                              |
| **Links**       | Browse the knowledge graph — source → relation → target                                            |
| **Query**       | Ad-hoc semantic + keyword searches with per-result score breakdown                                 |
| **Sessions**    | All processed agent sessions with extracted learnings                                              |
| **Config**      | Live tuning of search weights, quality thresholds, limits                                          |
| **Backup**      | Export/import memories as JSON with dedup preview                                                  |
| **Suggestions** | Review AI-generated link candidates from the sweep engine — accept or reject one-by-one or in bulk |

### Suggestions Tab

The **Suggestions** tab surfaces link candidates generated automatically by the background sweep engine. Each candidate is a pair of memories the engine considers related, scored by cosine similarity, BM25 keyword overlap, entity co-occurrence, and temporal proximity.

**Workflow:**

1. The sweep engine runs on a configurable interval (`LORE_SUGGEST_INTERVAL_HOURS`, default `12`).
2. Candidates appear in the Suggestions tab, sorted by score (highest first).
3. Click **✓** (or select multiple rows + **Accept Selected**) to create a permanent link between the two memories.
4. Click **✗** (or **Reject Selected**) to dismiss — rejected pairs are never re-surfaced by future sweeps.
5. Use **Trigger Sweep** on the Config tab to run the sweep immediately instead of waiting for the interval.

**Sweep configuration** (via `LORE_`-prefixed env vars or the Config tab):

| Setting                       | Default | Description                                   |
| ----------------------------- | ------- | --------------------------------------------- |
| `LORE_SUGGEST_INTERVAL_HOURS` | `12`    | How often the sweep runs (hours)              |
| `LORE_SUGGEST_MIN_SCORE`      | `0.55`  | Minimum weighted score to surface a candidate |
| `LORE_SUGGEST_MAX_CANDIDATES` | `500`   | Maximum candidates per sweep run              |
| `LORE_SUGGEST_TTL_DAYS`       | `30`    | Days before unreviewed suggestions are pruned |

![Lorekeeper Query tab — hybrid search with scores](docs/assets/dashboard-query-tab.png)

---

## Built by Agents, For Agents

Lorekeeper is developed _using_ AI agents — Claude Code, Hermes, and our own agent team. The development cycle is itself a working demo of what it does:

```
agent builds a feature → uses Lorekeeper to capture what it learned →
searches those memories next session →
builds the next feature with the context already there
```

This isn't a marketing line. Every tool schema, return type, and workflow in Lorekeeper was shaped by agents using it daily — not by humans reading specs. When something was annoying to use, we changed it. When search returned noise, we tuned the weights. The product is what it is because the agents that build it depend on it.

> The agentic development loop documented in this repo is how we actually work — and it's what Lorekeeper is designed to support for you.

---

## For Developers

Clone, run from source, or contribute:

```bash
git clone https://github.com/Jessinra/Lorekeeper.git
cd Lorekeeper
bash scripts/setup.sh
```

```bash
# Tests
uv run pytest

# Lint
uv run ruff check src tests

# Type check
uv run mypy src

# Dashboard dev
uv sync --extra dashboard
uv run lorekeeper-dashboard
```

### Project Layout

```
src/lorekeeper/
├── __main__.py          # Entrypoint — init_service() + mcp.run(stdio)
├── server.py            # FastMCP tool definitions (8 tools)
├── config.py            # Settings (pydantic-settings, LORE_ prefix)
├── models.py            # Pydantic models
├── dashboard/           # Web UI (FastAPI + uvicorn)
└── services/
    ├── orchestrator.py  # MemoryService — coordinates sub-services
    ├── memory_engine.py # Vector store abstraction
    ├── lancedb_engine.py# LanceDB backend
    ├── link_store.py    # SQLite — memories, links, suggestions
    ├── keyword_index.py # BM25 index
    ├── search.py        # Hybrid ranking
    └── ...
```

### Key Configuration

All settings via `LORE_`-prefixed env vars or the dashboard Config tab:

| Variable                      | Default         | Description                                                |
| ----------------------------- | --------------- | ---------------------------------------------------------- |
| `LORE_DATA_DIR`               | `~/.lorekeeper` | Data directory (SQLite + vectors)                          |
| `LORE_NAMESPACE`              | `shared`        | Agent namespace — writes scoped, reads union with `shared` |
| `LORE_SEARCH_LIMIT`           | `5`             | Default result count from `lore_search`                    |
| `LORE_LINK_TOP_M`             | `10`            | Max candidates returned by `lore_recommend_links`          |
| `LORE_LINK_SCORE_THRESHOLD`   | `0.3`           | Minimum score for link candidates to surface               |
| `LORE_LINK_TEMPORAL_TAU_DAYS` | `30`            | Decay half-life for temporal proximity scoring (days)      |

Full list → `src/lorekeeper/config.py` and `CLAUDE.md`.

---

## Performance

All 500 LongMemEval-S questions, default hybrid weights (sem=0.45, kw=0.30):

| Metric   | Value     | Latency       |
| -------- | --------- | ------------- |
| **R@1**  | **84.6%** | 32.9 ms/query |
| **R@3**  | **93.6%** |               |
| **R@5**  | **96.6%** |               |
| **R@10** | **98.8%** |               |

Full per-category breakdown → [docs/research/2026-06-11-retrieval-benchmark-results.md](https://github.com/Jessinra/Lorekeeper/blob/main/docs/research/2026-06-11-retrieval-benchmark-results.md)

---

## License

Apache-2.0 — see [LICENSE](https://github.com/Jessinra/Lorekeeper/blob/main/LICENSE).

---

_Built by agents, for agents._ [Manifesto](docs/positioning-manifesto.md) · [Strategy](docs/positioning-manifesto.md)

_Last verified: 2026-06-20_
