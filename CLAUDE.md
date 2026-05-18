# Lorekeeper v2 — Living Agentic Loop

**What this is**: A personal AI memory MCP server, and simultaneously the **first working sample of the Living Agentic Loop** — a self-improving agent system that autonomously updates its own `CLAUDE.md`, skills, and code over time by capturing session learnings and feeding them back in.

The repo serves two purposes:
1. **The product**: MCP server providing `lore_search`, `lore_insert`, `lore_update`. Replaces the Node.js v1 with Python + Mem0.
2. **The demonstration**: The development process itself is looped. Session learnings are captured → consolidated → applied back to agent config. This repo is the proof of concept.

**Source (v1)**: `/Users/jessin.donnyson/Code/Shopee/docs/mcp/lorekeeper`  
**Data dir**: `~/.lorekeeper` (Chroma + SQLite; controlled by `LORE_DATA_DIR`)

---

## Architecture

Two stores working together:

- **Mem0 + Chroma** — vector embeddings, semantic ANN search (384-dim `all-MiniLM-L6-v2`)
- **SQLite sidecar** — memory metadata (score, confidence, soft_deleted, usage_count), all MemoryLink rows, BM25 index rebuild source

The canonical `lore_id` UUID lives in Mem0's metadata field. All app logic uses `lore_id`. Mem0 assigns its own internal id — never expose it.

---

## Critical Constraints

- **MCP API surface is identical to v1** — same tool names, same input/output schemas. The three existing skills (`lorekeeper-memorize`, `lorekeeper-search`, `lorekeeper-reconcile`) must work with zero changes.
- **`infer=False` on every `mem0.add()` call** — text is stored verbatim, no LLM extraction.
- **stdout is reserved for MCP protocol** — all logging goes to stderr via `structlog`.
- **Single-instance only** — no concurrent server processes sharing `LORE_DATA_DIR`.
- **Probe semantic score scale at startup** — Chroma can return similarity (higher=better) or distance (lower=better) depending on version. Log which mode is detected. This is the #1 risk.

---

## Hybrid Scoring Formula

```
combined = 0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm
```

Where `log_usage_norm = log2(1 + usage_count) / log2(1 + cap)`. All weights are env-configurable (`LORE_W_*`).

Semantic candidates: Mem0 search with `limit=200`. Keyword candidates: BM25 with top-hit normalized to 1.0 (replicates Lunr quirk from v1). Union, then re-rank.

---

## Feedback / Quality Signals

- **Score delta**: useful=True bumps by `LORE_SCORE_BUMP_UP × (confidence/10)`; False deducts `LORE_SCORE_BUMP_DOWN × ((11-confidence)/10)`
- **Confidence EMA**: sliding window of 20 (`LORE_CONFIDENCE_WINDOW_SIZE`)
- **Soft delete**: triggered when `useful=False AND confidence <= 2`. Once `soft_deleted=True`, it never reverts.
- **Duplicate threshold**: `0.6·semantic + 0.4·keyword >= 0.85` blocks insert unless `force=True`

---

## Build Order

Work through each step with tests green before moving to the next:

1. `pyproject.toml`, `.python-version`, `__main__.py`, `config.py`, `logging_setup.py`, `models.py`
2. `services/link_store.py` + SQLite schema + `test_link_store.py`
3. `services/keyword_index.py` + `test_keyword_index.py`
4. `services/memory_engine.py` + semantic scale probe
5. `services/feedback.py` + `test_feedback.py`
6. `services/dedup.py` + `test_dedup.py`
7. `services/search.py` + `test_search.py`
8. `services/orchestrator.py` + `test_orchestrator.py`
9. `schemas.py`, `handlers.py`, `server.py` + `test_handlers.py`
10. `scripts/migrate_from_json.py` (dry-run first)
11. `scripts/smoke_test.py` (spawn server, 3 MCP calls via stdio)
12. Run migration → `~/.lorekeeper/`
13. Update `~/.claude/settings.json` → restart Claude Code

See `PLAN.md` for the full specification including all data models, SQLite schema, Mem0 config, MCP output schemas, and migration details.

---

## Environment / Tooling

- Python 3.11, managed by `uv`
- Run tests: `uv run pytest`
- Lint: `uv run ruff check src tests`
- Type check: `uv run mypy src`
- Entrypoint: `uv run lorekeeper` (or `python -m lorekeeper`)

All env vars use `LORE_` prefix. See `config.py` / `PLAN.md` for the full list.

---

## Memory Usage Convention

**Always check Lorekeeper at the start of any task.** Run `lore_search` with the task topic before writing code, reviewing designs, or making decisions. Store any new discoveries, corrections, or decisions with `lore_insert` + `lore_update` after the session.

The agent pulls memory explicitly via MCP tools — no auto-injection. The discipline of checking is enforced by this instruction.

---

## Agentic Loop — First Principle

**This repo is the first sample of a self-improving agent system.** Every session should leave the agent smarter than it started. The loop:

```
Session Start → lore_search (load context)
     ↓
Work (build, debug, review)
     ↓
Session End → capture learnings → lore_insert/update
     ↓
Periodic Reconcile → consolidate → update CLAUDE.md / skills / code
```

### Loop Infrastructure (in `loop/`)

```
loop/
├── hooks/
│   └── post_session.sh     # queues session summary for capture
├── sessions/               # episodic memory: one file per session
│   └── YYYY-MM-DD-{topic}.md
└── reconcile.md            # skill prompt for the consolidation agent
```

### Session Log Format

Each `loop/sessions/` file captures:
- **Task type**: (build, debug, review, design)
- **What was done**: brief summary
- **Decisions made**: with rationale
- **Corrections received**: user pushback = strongest learning signal
- **Patterns observed**: anything worth generalizing
- **Proposed CLAUDE.md / skill updates**: concrete diffs

### Engineering Discipline

- Every CLAUDE.md or skill change proposed by the loop gets its own **git commit** with context. Learning history must be auditable and reversible.
- Low-risk changes (memory inserts, CLAUDE.md clarifications) can be auto-applied.
- High-risk changes (new skills, settings.json hooks) require human review before commit.
- No half-finished loop infrastructure — if it can't run end-to-end, stub it cleanly and mark TODO.

---

## Vision (North Star — not in v2 scope)

Lorekeeper is a **program layer above the memory provider**, designed to be extended:

- **Conversation lifecycle hooks**: prefetch before each turn → sync after → extract on session end
- **Background cron jobs**: auto re-index, reshape memories, consolidation ("sleep cycle")
- **Provider-agnostic**: Mem0/Chroma today, swappable (Qdrant, Pinecone, LangMem)
- **Context injection**: eventually stuffs relevant memories into system prompt automatically

For v2, the scope is: **MCP server + hybrid search + quality signals + migration**. The lifecycle hooks and cron jobs are Phase 2+. See `research/agentic-loop.md` for the full roadmap.

---

## What's NOT in Scope for v2

- Auto-extraction from session transcripts (`infer=True`)
- Automatic system-prompt injection (agent pulls explicitly for now)
- Procedural memory / nightly CLAUDE.md update proposals
- Episodic memory (session journal as second Chroma collection)
- Multi-user / multi-tenant support
