# Lorekeeper v2 — Living Agentic Loop

**What this is**: A personal AI memory MCP server, and simultaneously the **first working sample of the Living Agentic Loop** — a self-improving agent system that autonomously updates its own `CLAUDE.md`, skills, and code over time by capturing session learnings and feeding them back in.

The repo serves two purposes:

1. **The product**: MCP server providing `lore_search`, `lore_remember`, `lore_insert`, `lore_update`. Replaces the Node.js v1 with Python + Mem0.
2. **The demonstration**: The development process itself is looped. Session learnings are captured → consolidated → applied back to agent config. This repo is the proof of concept.

**Data dir**: `~/.lorekeeper` (Chroma or LanceDB + SQLite; controlled by `LORE_DATA_DIR`; set `LORE_VECTOR_STORE=lancedb` to switch)

---

## Architecture

Two stores working together:

- **Chroma (default) or LanceDB** — vector embeddings, semantic ANN search (384-dim `all-MiniLM-L6-v2`). Set `LORE_VECTOR_STORE=lancedb` to use LanceDB for concurrent multi-process access. See `backlogs/LKPR-31-switch-to-lancedb-vector-store.md`.
- **SQLite sidecar** — memory metadata (score, confidence, soft_deleted, usage_count), all MemoryLink rows, BM25 index rebuild source

The canonical `lore_id` UUID lives in Mem0's metadata field. All app logic uses `lore_id`. Mem0 assigns its own internal id — never expose it.

### SQLite store decomposition (LKPR-51)

The SQLite layer is split into a shared `Database` class (owning the connection lifecycle + versioned migrations) and five focused stores, each handling one domain:

| Store | Owns | File |
|---|---|---|
| `Database` | SQLite connection (WAL mode, FKs), versioned migrations (`_schema_version` table) | `services/database.py` |
| `MemoryStore` | `memories` table CRUD | `services/memory_store.py` |
| `LinkStore` | `memory_links` table CRUD | `services/link_store.py` |
| `ReflectionStore` | `reflections` + `sessions` (FK-coupled) | `services/reflection_store.py` |
| `MetricsStore` | `api_metrics` table | `services/metrics_store.py` |
| `ConfigStore` | `config_overrides` table | `services/config_store.py` |

All stores share a single `Database` instance — they receive it via constructor and use its `conn` property. The `MemoryService` orchestrator exposes them as public attributes (`svc.memories`, `svc.links`, `svc.reflections`, `svc.metrics`, `svc.config`, `svc.settings`).

**Migrations**: `Database.migrate()` applies entries from the `MIGRATIONS` list in version order, recording applied versions in `_schema_version`. The current `MIGRATIONS[0]` (version 1, `bootstrap_schema_and_fixups`) captures all pre-LKPR-51 schema setup + idempotent fixups. Add new schema changes as `MIGRATIONS.append((N, name, fn))` with strictly-increasing version numbers.

---

## Critical Constraints

- **MCP API surface is identical to v1** — same tool names, same input/output schemas. The three existing skills (`lorekeeper-memorize`, `lorekeeper-search`, `lorekeeper-reconcile`) must work with zero changes.
- **`infer=False` on every `mem0.add()` call** — text is stored verbatim, no LLM extraction.
- **stdout is reserved for MCP protocol** — all logging goes to stderr via `structlog`.
- **Probe semantic score scale at startup** — Chroma can return similarity (higher=better) or distance (lower=better) depending on version. Log which mode is detected. This is the #1 risk. LanceDB always returns cosine distance (converted to similarity internally).

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
- Lint (Python): `uv run ruff check src tests`
- Lint (JS): `npx @biomejs/biome check src/lorekeeper/dashboard/static/js/`
- Type check: `uv run mypy src` (run before push; not in pre-commit — too slow)
- Entrypoint: `uv run lorekeeper` (or `python -m lorekeeper`)

Pre-commit hook blocks commit on lint/test failures. Install: `bash scripts/setup.sh`.
See `docs/linter-decisions.md` for rule selection rationale.

All env vars use `LORE_` prefix. See `config.py` / `PLAN.md` for the full list.

| Env var | Default | Purpose |
|---|---|---|
| `LORE_DATA_DIR` | `~/.lorekeeper` | Where SQLite + vector DB live |
| `LORE_NAMESPACE` | `shared` | Agent write namespace. Writes tagged with this value; reads return union of `[namespace, "shared"]`. Set automatically by `setup.sh` for Hermes profiles. |
| `LORE_SEARCH_LIMIT` | `5` | Default number of results returned by `lore_search` |
| `LORE_MAX_SEARCH_IDS` | `50` | Max IDs in `lore_search(ids=[...])` bulk lookup — enforced at handler layer |
| `LORE_MAX_REFINE_FROM_IDS` | `200` | Max IDs in `lore_search(refine_from=[...])` — enforced at handler layer |

### First-Time Setup

Run this once (or after updating skills or agent configs):

```bash
./scripts/setup.sh
```

**What it does (smart multi-agent setup):**

1. **Detects installed agents** — scans for Hermes (main + all profiles), Claude Code (`~/.claude`), and Cursor (`~/.cursor`) automatically.
2. **Injects MCP entry** — adds `lorekeeper` under `mcpServers`/`mcp_servers` in each agent's config file with `LORE_DATA_DIR` and `LOREKEEPER_SETUP_VERSION` env vars. Idempotent — skips if already present.
3. **Injects prompt** — upserts a `## Lorekeeper` section into each agent's prompt file (`soul.md`, `CLAUDE.md`, `.cursorrules`, `AGENTS.md`) from `assets/prompts/lorekeeper-agent-prompt.md`. Version-stamped — only re-injects when the source version changes.
4. **Installs skills** — syncs `assets/skills/` (user-facing, copied) and `.hermes/skills/` (dev, symlinked with category dirs) into each agent's skills directory.

Re-run after:

- Editing any skill in `.hermes/skills/` or `assets/skills/`
- Updating `assets/prompts/lorekeeper-agent-prompt.md`
- Adding a new agent install (new Hermes profile, fresh Cursor, etc.)

**Prompt source of truth:** `assets/prompts/lorekeeper-agent-prompt.md` — edit this file to change the Lorekeeper section injected into all agents.

---

## Memory Usage Convention

**Always check Lorekeeper at the start of any task.** Run `lore_search` with the task topic before writing code, reviewing designs, or making decisions. Store any new discoveries, corrections, or decisions with `lore_remember` (for quick single thoughts) or `lore_insert` (for structured memories) + `lore_update` after the session.

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

For v2, the scope is: **MCP server + hybrid search + quality signals + migration**. The lifecycle hooks and cron jobs are Phase 2+. See `docs/plans/agentic-loop.md` for the full roadmap.

---

## Plans Location

Implementation plans live in `docs/plans/YYYY-MM-DD_HHMMSS-<slug>.md` (not `.hermes/plans/`). This is the project-specific override of the global `plan` skill default. Keep plans organized and named by date + topic slug.

---

## Commit Convention

All commits are enforced by `.git/hooks/commit-msg` (installed via `./scripts/setup.sh`).

**Author identity** (set once per clone):

```bash
# PM
git config --local user.name "Akane (PM)"
git config --local user.email "jessinra.kai@gmail.com"

# Dev
git config --local user.name "Dev"
git config --local user.email "jessinra.kai@gmail.com"

# Diana
git config --local user.name "Diana"
git config --local user.email "jessinra.kai@gmail.com"
```

**Commit title format**: `[LKPR-N] type: short imperative title`

- `[LKPR-N]` — work tied to a specific ticket
- `[LKPR-0]` — housekeeping with no ticket (chore, backlog edits, skill updates, status changes)
- Merge commits to main are exempt

Full details → `commit-convention` skill.

---

## Post-Change Rule

After **every set of code changes**, load the `after-changes` skill and follow it. It covers three steps in order:

1. Code review — fix reuse, quality, and efficiency issues
2. README consistency check — update `README.md` for anything that drifted
3. Git commit — stage and commit with a descriptive message

**Opening PRs:** load the `github-pr` skill. In short:

```bash
gh pr create --base main --title "[LKPR-N] type: short imperative title" --body "[see .github/PULL_REQUEST_TEMPLATE.md]" --reviewer @copilot
```

PR title format: same as commit — `[LKPR-N] type: imperative title`. This is enforced by the PR template at `.github/PULL_REQUEST_TEMPLATE.md`.

Do not skip this. It is the discipline that keeps the repo clean and auditable.

---

## Git Workflow — Hard Rules

### NEVER merge to main directly

- **All changes go through feature branches** (`LKPR-*`, `feat/*`, `fix/*`) — never work on `main`
- **All feature branches MUST go through a PR** before reaching `main`
- **The pre-commit hook blocks commits on `main`** — a deliberate hard stop. Use `git checkout -b <branch>` first.
- **`git push origin main` is ALWAYS wrong** unless you are the CI/CD pipeline
- **`git checkout main && git merge <branch>` runs on a local feature branch** — push the feature branch, open a PR, merge via the web UI
- This rule applies to ALL agents — Hermes, Claude Code, Cursor. No exceptions without human approval.

**The workflow is always:**

```
feature branch → push → PR → review → merge via GitHub UI → delete branch
```

---

## Backlog Management

All ticket workflow — lifecycle, numbering, scripts, filing conventions, and pitfalls — is documented in the `backlog-management` skill. Load it with `skill_view('backlog-management')` when working with tickets.

---

## README Consistency

When editing any file in `src/lorekeeper/`, `pyproject.toml`, or `loop/`, check `README.md` for claims about that file and verify they are still accurate. Key things to watch:

- **Config defaults** — `config.py` field defaults must match the README config table
- **Env var names** — derived from field names + `LORE_` prefix (pydantic-settings)
- **Tool signatures** — `server.py` parameter names and defaults must match README tool examples
- **Dashboard port** — `dashboard/__init__.py` default port must match README
- **Dedup formula** — `services/dedup.py` weights must match README description
- **Project layout** — new or renamed modules must be reflected in the README layout tree

---

## What's NOT in Scope for v2

- Auto-extraction from session transcripts (`infer=True`)
- Automatic system-prompt injection (agent pulls explicitly for now)
- Procedural memory / nightly CLAUDE.md update proposals
- Episodic memory (session journal as second Chroma collection)
- Multi-user / multi-tenant support
