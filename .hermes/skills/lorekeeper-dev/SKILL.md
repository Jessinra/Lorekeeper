---
name: lorekeeper-dev
description: Engineering practices for developing the Lorekeeper codebase. Load this skill when working on Lorekeeper source code, fixing bugs, adding features, writing tests, or reviewing PRs. Covers architecture conventions, SQLite/LanceDB/Chroma quirks, testing patterns, and the verification standard for shipped changes. For backlog/ticket workflow, see backlog-management skill.
version: v2.5.0
tags: []
related_skills: [backlog-management, after-changes]
---

# Lorekeeper Dev

Practices and conventions for developing the Lorekeeper MCP server.

## Architecture

Two vector store backends (switch via `LORE_VECTOR_STORE`):

- **LanceDB** (default) — concurrent multi-process, no lock files. `LanceDBEngine` in `lancedb_engine.py`. Uses sentence-transformers directly, no Mem0 for vectors.
- **Chroma** (fallback, `LORE_VECTOR_STORE=chroma`) — Mem0-backed `ChromaDBEngine` in `chromadb_engine.py`. Single-process only.
- **SQLite sidecar** — memory metadata (`score`, `confidence`, `soft_deleted`, `usage_count`), all `MemoryLink` rows, BM25 index source. Shared by both backends.

Engine factory: `engine_factory.py` → `build_engine()`. Orchestrator: `MemoryService` in `orchestrator.py`.

Canonical identity: `lore_id` UUID lives in the vector store's metadata. All app logic uses `lore_id`.

## Hybrid Scoring Formula

```
combined = 0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm
```

Weights are env-configurable (`LORE_W_*`). Dedup threshold: `0.6·semantic + 0.4·keyword >= 0.85`.

## Known Quirks

**Chroma distance vs. similarity (critical):** Mem0 v2 `score_and_rank` receives Chroma cosine _distances_ but treats them as similarities. **Fix**: bypass mem0 pipeline — embed directly with `SentenceTransformer`, query directly, return `score = 1.0 - distance`.

**LanceDB:** Always returns cosine distance (lower=better). `normalize_score()` converts to similarity: `1.0 - distance`.

**`infer=False` on every `mem0.add()` call** — text stored verbatim, no LLM extraction.

**stdout reserved for MCP protocol** — all logging to stderr via `structlog`.

## Tooling

```bash
uv run pytest                          # run tests
uv run pytest tests/ -x -q            # fail-fast
uv run ruff check src tests            # lint (Python)
uv run ruff check src tests --fix      # auto-fix lint
uv run mypy src                        # type check (run before push)
npx @biomejs/biome check src/lorekeeper/dashboard/static/js/    # lint (JS)
uv run lorekeeper                      # start server
```

## Pre-commit Hook

Install via `bash scripts/setup.sh`. Runs: 1. `ruff check src tests`, 2. `biome check`, 3. `uv run pytest tests/ -q`.

## Setup Script — `scripts/setup.sh`

Detects installed agents (Hermes, Claude Code, Cursor), injects MCP entry, upserts Lorekeeper prompt, syncs skills. Run from repo root:

```bash
./scripts/setup.sh
```

**Verification:** Hermes config has `lorekeeper:` under `mcp_servers`; `soul.md` has `## Lorekeeper` section; skills symlinks exist; all skills are versioned `v{M.m.m}`.

## Testing Patterns

- Table-driven tests for multiple cases
- Descriptive naming: `test_search_unrelated_query_scores_below_threshold`
- Real (not mocked) vector store for memory_engine tests
- Seed distinct memories before asserting search behavior

## Branch Naming

Format: `<type>/LKPR-N-short-description`. Types: `feature/`, `fix/`, `hotfix/`, `refactor/`, `chore/`, `docs/`.

Rules: kebab-case only, always include LKPR-N ID, branch off `main`, delete after merging. No direct pushes to main — only PR merges.

## Commit Messages

Format: `[LKPR-N] type: short imperative title`. `[LKPR-0]` for housekeeping.

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`.

Rules: one logical change per commit, no WIP in main, author name must be `Dev` or `Diana`, email `jessinra.kai@gmail.com`.

## Backlog Workflow

Tickets live in `backlogs/` as `LKPR-N-slug.md`. Status tracked via GitHub Issue labels.

```bash
gh issue edit LKPR-30 --add-label "S:In-progress" --remove-label "S:Ready"
```

## Coding Standards

| Rule            | Limit                                    |
| --------------- | ---------------------------------------- |
| File length     | 200–400 lines typical, **800 max**       |
| Function length | **50 lines max**                         |
| Nesting depth   | **4 levels max** — use early returns     |
| Mutation        | **Avoid** — prefer returning new objects |

`scripts/` naming: Python = `snake_case.py`, shell = `kebab-case.sh`.

## Verification Standard

Every fix or feature must have: root cause documented, before/after evidence, regression test.

## Self-Testing Discipline

Every fix needs a test that would have caught the bug. Every feature needs tests covering happy path + at least one edge case.

Test naming: `def test_<unit>_<scenario>_<expected_outcome>()`.

Discipline: run `uv run pytest` before every push, never skip tests without a comment, don't mock Mem0/Chroma in memory_engine tests.

## GitHub CLI (`gh`)

Uses `jessinra-megumi-dev[bot]` for all operations. Token auto-refreshes every 45 min.

```bash
git push -u origin HEAD
gh pr create --base main --title "[LKPR-N] type: title" --body "## Summary\n\nCloses LKPR-N"
gh pr view 12
gh pr merge 12 --squash --delete-branch
```

## Code Review Standards

See `references/code-review-standards.md` for the full review checklist (general engineering, clean code, Python/JS specifics, security, cross-cutting constraints, performance).

## Pre-Push Self-Review Checklist

See `references/pre-push-checklist.md` for the complete checklist (correctness, tests, code quality, docs, git).

## PM Expectations

See `references/pm-expectations.md` for what Akane checks on every review.

## Post-Change Rule

See `references/post-change-rule.md` for the commit timing and full sequence.

## Plans Location

Implementation plans in `docs/plans/YYYY-MM-DD_HHMMSS-<slug>.md` — not `.hermes/plans/`.

## Skills Distribution

Skills for **Lorekeeper users/clients** live in `assets/skills/`. Skills for the **dev agent** live in `.hermes/skills/`. Run `scripts/setup.sh` to symlink them.
