---
name: lorekeeper-dev
description: Engineering practices for developing the Lorekeeper codebase. Load this skill when working on Lorekeeper source code, fixing bugs, adding features, writing tests, or reviewing PRs. Covers architecture conventions, SQLite/Mem0/Chroma quirks, testing patterns, backlog workflow, and the verification standard for shipped changes.
version: 1.0.0
---

# Lorekeeper Dev

Practices and conventions for developing the Lorekeeper MCP server.

## Architecture

Two stores working together:
- **Mem0 + Chroma** — vector embeddings, semantic ANN search (`all-MiniLM-L6-v2`, 384-dim)
- **SQLite sidecar** — memory metadata (`score`, `confidence`, `soft_deleted`, `usage_count`), all `MemoryLink` rows, BM25 index source

Canonical identity: `lore_id` UUID lives in Mem0's metadata field. All app logic uses `lore_id`. Never expose Mem0's internal id.

## Hybrid Scoring Formula

```
combined = 0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm
```

Weights are env-configurable (`LORE_W_*`). Dedup threshold: `0.6·semantic + 0.4·keyword >= 0.85`.

## Known Quirks

**Chroma distance vs. similarity (critical):**  
Mem0 v2 `score_and_rank` receives Chroma cosine *distances* (0=identical) but treats them as similarities — items with distance ~0.0 get filtered out; unrelated items (distance ~1.0) score 1.0 and block all inserts.  
**Fix**: bypass mem0 pipeline in `memory_engine.py#search()` — embed directly with `SentenceTransformer`, query `self._mem0.vector_store.collection.query()`, return `score = 1.0 - distance`.

**`infer=False` on every `mem0.add()` call** — text stored verbatim, no LLM extraction.

**stdout reserved for MCP protocol** — all logging to stderr via `structlog`.

## Tooling

```bash
uv run pytest                          # run tests
uv run pytest tests/ -x -q            # fail-fast
uv run ruff check src tests            # lint
uv run mypy src                        # type check
uv run lorekeeper                      # start server
```

## Testing Patterns

- Table-driven tests where multiple cases exist
- Name cases descriptively: `"scores vary for semantically distinct memories"`
- Always use real (not mocked) Mem0+Chroma for memory_engine tests — mocks hide the distance/similarity inversion bug
- Seed distinct memories before asserting search behavior

## Backlog Workflow

Tickets live in `backlogs/` as dated slugs (e.g. `2026-05-22-lore-insert-false-dedup.md`), not `LKPR-N.md` filenames.

After shipping a fix:
1. Update the ticket: add root cause, before/after evidence, tests added
2. Set `status: done` and `resolved_date: YYYY-MM-DD`

## Verification Standard

Every fix or feature must have:
- **Root cause** documented in the backlog ticket (not just "fixed X")
- **Before/after evidence** — concrete scores, outputs, or test results
- **Regression test** — assert the fix can't silently regress

## Post-Change Rule

After every set of changes:
1. Code review — check reuse, quality, efficiency
2. README consistency — verify config defaults, tool signatures, env var names still match
3. Commit with descriptive message
4. Push to both `origin` (GitHub) and `gitlab`

## Skills Distribution

Skills for **Lorekeeper users/clients** live in `assets/skills/` in this repo — one folder per skill, matching the standard `skill-name/SKILL.md` structure. These are distributed to users alongside the server.

Skills for the **dev agent** (engineering practices, internal tooling) live in your `$AGENTIC_HOME/skills/` and are NOT copied to `assets/skills/`.
