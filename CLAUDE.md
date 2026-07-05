# Lorekeeper v2 — Living Agentic Loop

**What this is**: A personal AI memory MCP server, and simultaneously the **first working sample of the Living Agentic Loop** — a self-improving agent system that autonomously updates its own `CLAUDE.md`, skills, and code over time by capturing session learnings and feeding them back in.

The repo serves two purposes:

1. **The product**: MCP server providing `lore_search`, `lore_remember`, `lore_insert`, `lore_update`, `lore_forget`, `lore_recommend_links`. Replaces the Node.js v1 with Python + LanceDB.
2. **The demonstration**: The development process itself is looped. Session learnings are captured → consolidated → applied back to agent config. This repo is the proof of concept.

**Data dir**: `~/.lorekeeper` (LanceDB + SQLite; controlled by `LORE_DATA_DIR`)

---

## Architecture — Six-Layer (LKPR-105)

Lorekeeper follows a strict 6-layer architecture with **unidirectional imports** — a layer may import from layers below it, never above.

````text
┌──────────────────────────────────────────────────────────────┐
│  api/mcp/, dashboard/, server.py, cli/                       │ Layer 6 — Interface adapters
├──────────────────────────────────────────────────────────────┤
│  shared/ (serializers, encouragement)                        │ Layer 5 — Presentation helpers
├──────────────────────────────────────────────────────────────┤
│  processors/ (memory, link, reflection, suggestion, admin)   │ Layer 4 — Orchestration
├──────────────────────────────────────────────────────────────┤
│  domains/{memory,link,reflection,suggestion}/                │ Layer 3 — Business logic
├──────────────────────────────────────────────────────────────┤
│  platform/{config,metrics}/                                  │ Layer 2 — Supporting repos
├──────────────────────────────────────────────────────────────┤
│  infra/ (database, search_engine, keyword_index,             │ Layer 1 — Zero business
│         scheduler, logging_setup, settings)                  │           vocabulary
└──────────────────────────────────────────────────────────────┘
```text

### Import rules

- `infra` imports NOTHING from lorekeeper except other `infra` modules
- `platform` imports only `infra`
- `domains` import `platform`, `infra`, and other domains (per DAG below) — never `shared`, `api`, `dashboard`, `server`
- `shared` imports `domains` and below (it serializes domain models for the API layer)
- `processors` import `domains`, `platform`, `infra` — never each other (no `processors.X` imports `processors.Y`)
- `api`/`dashboard`/`server`/`cli` import anything below
- `server.py` is exempt from layer rules (composition root imports everything)

### Cross-domain DAG (acyclic)

```text
suggestion ──→ memory ──→ link
reflection ──→ memory
```text

`link` depends on no other domain. No cycles.

### Layer Responsibilities

| Layer                                          | Owns                                                                                                  | Does NOT own                                           |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **Presentation** (api, dashboard, server, cli) | MCP tool routing, HTTP routing, serialization, encouragement wrappers                                 | Validation, metrics, commit, business rules            |
| **shared/**                                    | Serialization format (SearchResult → dict), encouragement text injection                              | Business logic, stores                                 |
| **processors/**                                | Input validation, metric increments, commit boundaries, batch loops                                   | Serialization, single-aggregate business rules         |
| **domains/**                                   | Single-aggregate business rules (dedup, scoring, feedback, search ranking, link candidate generation) | Validation (beyond domain invariants), metrics, commit |
| **platform/**                                  | Supporting subdomain repos (config overrides, metrics storage)                                        | Business logic                                         |
| **infra/**                                     | Database connection + migrations, vector search engine, keyword index, scheduler, settings            | Business vocabulary                                    |

### Key stores (all in `domains/*/repository.py` or `platform/`)

| Store                 | Class                 | Location                           |
| --------------------- | --------------------- | ---------------------------------- |
| `Database`            | `Database`            | `infra/database.py`                |
| `MemoryStore`         | `MemoryStore`         | `domains/memory/repository.py`     |
| `LinkStore`           | `LinkStore`           | `domains/link/repository.py`       |
| `ReflectionStore`     | `ReflectionStore`     | `domains/reflection/repository.py` |
| `LinkSuggestionStore` | `LinkSuggestionStore` | `domains/suggestion/repository.py` |
| `MetricsStore`        | `MetricsStore`        | `platform/metrics/repository.py`   |
| `ConfigStore`         | `ConfigStore`         | `platform/config/repository.py`    |

- No `MemoryService` facade — `server.py` is the sole composition root
- All stores share a single `Database` instance via constructor injection
- **Migrations**: `Database.migrate()` applies entries from the `MIGRATIONS` list in version order

---

## Critical Constraints

- **MCP API surface is identical to v1** — same tool names, same input/output schemas. The three existing skills (`lorekeeper-memorize`, `lorekeeper-search`, `lorekeeper-reconcile`) must work with zero changes.
- **No LLM extraction on add** — text is stored verbatim, no inference or rewriting.
- **stdout is reserved for MCP protocol** — all logging goes to stderr via `structlog`.
- **Probe semantic score scale at startup** — LanceDB always returns cosine distance (converted to similarity internally).

---

## Hybrid Scoring Formula

```text
combined = 0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm
```text

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

1. `pyproject.toml`, `.python-version`, `__main__.py`, `infra/settings.py`, `infra/logging_setup.py`, `domains/memory/models.py`
2. `infra/database.py` + migrations + `test_database.py`
3. `domains/link/repository.py` + `test_link_repository.py`
4. `domains/memory/repository.py` + `test_memory_repository.py`
5. `infra/search_engine.py` + semantic scale probe
6. `domains/memory/service.py` (MemorySearchService + MemoryWriteService) + `test_search_service.py` + `test_write_service.py`
7. `domains/memory/dedup.py` + `test_dedup.py`
8. `domains/memory/feedback.py` + `test_feedback.py`
9. `infra/keyword_index.py` + `test_keyword_index.py`
10. `domains/reflection/service.py` + `test_reflection_service.py`
11. `domains/suggestion/service.py` + `test_suggestion_service.py`
12. `processors/` — memory, link, reflection, suggestion, admin + processor tests
13. `server.py` (composition root) + `test_handlers.py`
14. `scripts/migrate_from_json.py` (dry-run first)
15. `scripts/smoke_test.py` (spawn server, 3 MCP calls via stdio)
16. Run migration → `~/.lorekeeper/`
17. Update `~/.claude/settings.json` → restart Claude Code

Layering is enforced by `tests/test_architecture.py`, not by human review — if you need a new cross-layer edge, add it to the test's allowed-edges table with a comment.

---

## Environment / Tooling

- Python 3.11, managed by `uv`
- Run tests (unit): `uv run pytest` — E2E tests are excluded by default
- Run E2E tests: `uv run playwright install chromium` (once), then `uv run pytest tests/e2e/ -m e2e`
- **Pre-PR rule**: if you added or changed E2E tests, run the E2E suite locally before opening the PR. Unit CI pass does NOT catch E2E infra bugs (hook signature errors, addopts conflicts, pipe deadlocks).
- **CI**: the `e2e` job in `.github/workflows/ci.yml` is intentional and must never be removed.
- Coverage report (optional): `bash scripts/test-coverage.sh`
- Lint (Python): `uv run ruff check src tests scripts/`
- Lint (JS): `npx @biomejs/biome check src/lorekeeper/dashboard/static/js/`
- Lint (Markdown): `while IFS= read -r -d '' f; do [ -f "$f" ] && printf '%s\0' "$f"; done < <(git ls-files -z '*.md') | xargs -0 npx --yes prettier@3.5.3 --check --prose-wrap preserve`
- Type check: `uv run mypy src` (run before push; not in pre-commit — too slow)
- Entrypoint: `uv run lorekeeper` (or `python -m lorekeeper`)
- Build docs (local preview): `uv sync --group docs && uv run mkdocs serve`
- Build docs (strict): `uv run mkdocs build --strict`
- Pre-PR rule: always run `mkdocs build --strict` before opening a PR that touches `mkdocs.yml`, `docs/`, or `README.md`.

Pre-commit hook (~3s): branch guard, ticket format, ruff, biome, prettier, mcp docs, skill format. Install: `bash scripts/setup.sh`.
Pre-push hook (~65s): mypy, unit tests, E2E tests (skipped gracefully if Playwright/Chromium not installed).
See `docs/linter-decisions.md` for rule selection rationale.

All env vars use `LORE_` prefix. See `config.py` / `PLAN.md` for the full list.

| Env var                              | Default          | Purpose                                                                                                                                                   |
| ------------------------------------ | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LORE_DATA_DIR`                      | `~/.lorekeeper`  | Where SQLite + vector DB live                                                                                                                             |
| `LORE_NAMESPACE`                     | `shared`         | Agent write namespace. Writes tagged with this value; reads return union of `[namespace, "shared"]`. Set automatically by `setup.sh` for Hermes profiles. |
| `LORE_SEARCH_LIMIT`                  | `5`              | Default number of results returned by `lore_search`                                                                                                       |
| `LORE_MAX_SEARCH_IDS`                | `50`             | Max IDs in `lore_search(ids=[...])` bulk lookup — enforced at handler layer (bypassing the handler bypasses this cap)                                     |
| `LORE_MAX_REFINE_FROM_IDS`           | `200`            | Max IDs in `lore_search(refine_from=[...])` — enforced at handler layer (bypassing the handler bypasses this cap)                                         |
| `LORE_LINK_TOP_K`                    | `50`             | Cosine pre-filter: top-K candidates per memory before scoring                                                                                             |
| `LORE_LINK_TOP_M`                    | `10`             | Max candidates returned by `lore_recommend_links`                                                                                                         |
| `LORE_LINK_SCORE_THRESHOLD`          | `0.3`            | Minimum Stage 1 weighted score to pass                                                                                                                    |
| `LORE_LINK_WEIGHT_COSINE`            | `0.5`            | Cosine similarity weight in combined score                                                                                                                |
| `LORE_LINK_WEIGHT_BM25`              | `0.3`            | BM25 keyword overlap weight                                                                                                                               |
| `LORE_LINK_WEIGHT_ENTITY`            | `0.1`            | Entity overlap (spaCy NER) weight                                                                                                                         |
| `LORE_LINK_WEIGHT_TEMPORAL`          | `0.1`            | Temporal proximity weight                                                                                                                                 |
| `LORE_LINK_TEMPORAL_TAU_DAYS`        | `30`             | Decay half-life for temporal scorer (days)                                                                                                                |
| `LORE_LINK_SPACY_MODEL`              | `en_core_web_sm` | spaCy model for entity overlap scorer                                                                                                                     |
| `LORE_SUGGEST_HIGH_CONFIDENCE_SCORE` | `0.85`           | Min weighted score for `confidence='high'` tag on sweep suggestions                                                                                       |
| `LORE_SUGGEST_INTERVAL_HOURS`        | `12`             | Time between full link-suggestion sweeps                                                                                                                  |
| `LORE_SUGGEST_TTL_DAYS`              | `30`             | TTL for unacted suggestions in days                                                                                                                       |
| `LORE_SUGGEST_POLL_SECONDS`          | `300`            | Scheduler daemon poll interval in seconds                                                                                                                 |

### Periodic Jobs (Internal Scheduler)

A generic `PeriodicJob` daemon thread runs inside the MCP server process. Each job persists its schedule in `config_overrides["{name}_next_run_at"]`, surviving restarts.

**Sweep job (LKPR-99):** Implemented as a standalone `SweepService` in `domains/suggestion/sweep.py` — not coupled to the old `MemoryService` facade. Checks the timer every `LORE_SUGGEST_POLL_SECONDS` (default 5 min). When elapsed, fires `run()`:

1. Iterates all active memories
2. Runs the existing `LinkCandidateGenerator` on each memory
3. Stores scored candidates in the `link_suggestions` table
4. Tags high-confidence pairs (`weighted_score >= 0.85 → confidence='high'`)
5. Skips already-linked and previously-rejected pairs
6. Prunes suggestions older than `LORE_SUGGEST_TTL_DAYS` (default 30)

**No real `memory_links` rows are created.** All suggestions are purely in `link_suggestions` for future agent review (LKPR-100) or dashboard (LKPR-101). The stored scores + confidence labels form training data for a future classifier.

Scheduler is crash-safe: exceptions are caught and logged, never crashes the server. On fresh DB (no `sweep_next_run_at` key), the first sweep fires immediately on the first poll cycle.

Standalone entrypoint: `python scripts/sweep-links.py --data-dir <path> --dry-run`.

### First-Time Setup

For **end users** (pip install): run the bundled Python command:

```bash
lorekeeper setup
````

For **contributors** (git clone): run the bash script which also installs dev hooks and dev skills:

```bash
./scripts/setup.sh
```

**What `lorekeeper setup` does:**

1. **Detects installed agents** — scans for Hermes (main + all profiles), Claude Code (`~/.claude`), and Cursor (`~/.cursor`) automatically.
2. **Injects MCP entry** — adds `lorekeeper` under `mcpServers`/`mcp_servers` in each agent's config file with `LORE_DATA_DIR`. Idempotent — skips if already present.
3. **Injects prompt** — upserts a `## Lorekeeper` section into each agent's prompt file (`soul.md`, `CLAUDE.md`, `AGENTS.md`) from the bundled `assets/prompts/lorekeeper-agent-prompt.md`.
4. **Installs skills** — syncs `assets/skills/` (user-facing) into each agent's skills directory.

Use `lorekeeper setup --check` for a dry-run that shows what would be configured without writing anything.

`scripts/setup.sh` additionally installs dev-only hooks and `.hermes/skills/` (symlinked with category dirs) — contributors should prefer it.

Re-run after:

- Editing any skill in `.hermes/skills/` or `src/lorekeeper/assets/skills/`
- Updating `src/lorekeeper/assets/prompts/lorekeeper-agent-prompt.md`
- Adding a new agent install (new Hermes profile, fresh Cursor, etc.)

**Prompt source of truth:** `src/lorekeeper/assets/prompts/lorekeeper-agent-prompt.md` — edit this file to change the Lorekeeper section injected into all agents.

---

## Memory Usage Convention

**Always check Lorekeeper at the start of any task.** Run `lore_search` with the task topic before writing code, reviewing designs, or making decisions. Store any new discoveries, corrections, or decisions with `lore_remember` (for quick single thoughts) or `lore_insert` (for structured memories) + `lore_update` after the session.

The agent pulls memory explicitly via MCP tools — no auto-injection. The discipline of checking is enforced by this instruction.

---

## Agentic Loop — First Principle

**This repo is the first sample of a self-improving agent system.** Every session should leave the agent smarter than it started. The loop:

````text
Session Start → lore_search (load context)
     ↓
Work (build, debug, review)
     ↓
Session End → capture learnings → lore_insert/update
     ↓
Periodic Reconcile → consolidate → update CLAUDE.md / skills / code
```text

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
- **Provider-agnostic vector layer**: LanceDB today, swappable (Qdrant, Pinecone)
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
````

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

````text
feature branch → push → PR → review → merge via GitHub UI → delete branch
```text

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
- **Dedup formula** — `domains/memory/dedup.py` weights must match README description
- **Project layout** — new or renamed modules must be reflected in the README layout tree

---

## What's NOT in Scope for v2

- Auto-extraction from session transcripts (`infer=True`)
- Automatic system-prompt injection (agent pulls explicitly for now)
- Procedural memory / nightly CLAUDE.md update proposals
- Episodic memory (session journal as a second vector collection)
- Multi-user / multi-tenant support
````
