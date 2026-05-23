---
name: lorekeeper-dev
description: Engineering practices for developing the Lorekeeper codebase. Load this skill when working on Lorekeeper source code, fixing bugs, adding features, writing tests, or reviewing PRs. Covers architecture conventions, SQLite/Mem0/Chroma quirks, testing patterns, and the verification standard for shipped changes. For backlog/ticket workflow, see backlog-management skill.
version: 2.0.0
tags: []
related_skills: [backlog-management, after-changes]
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

## Branch Naming

Format: `<type>/LKPR-N-short-description`

Types: `feature/`, `fix/`, `hotfix/`, `refactor/`, `chore/`, `docs/`

Examples:
```
feature/LKPR-7-lore-init-onboarding
fix/LKPR-19-fk-constraints-link-store
chore/LKPR-13-sleep-cycle-consolidation
refactor/LKPR-4-context-budgeting
```

Rules:
- kebab-case only, no underscores
- always include the LKPR-N ID
- branch off `main`
- delete after merging

---

## Commit Messages

Format:
```
[LKPR-N] type: short title

Body explaining what changed and why.
- file.py: what changed
- test.py: what covers it
- backlog: marked done
```

For chore work without a ticket: use `[LKPR-dev]` as prefix.

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

Examples:
```
[LKPR-6] feat: add iterative search with relevance cutoff
[LKPR-19] fix: enable FK constraints via PRAGMA foreign_keys=ON
[LKPR-16] test: add regression tests for scoring fix
[LKPR-dev] chore: rename backlog tickets with LKPR-N prefix
```

Rules:
- one logical change per commit — if you need "and", split it
- never bundle unrelated changes
- no WIP commits in main — squash before merging

---

## Backlog Workflow

> Full details → load the `backlog-management` skill. Brief summary below:

Tickets live in `backlogs/` as `LKPR-N-slug.md`. Completed → `backlogs/done/`. Numbering: sequential (highest+1), never fill gaps.

**Picking up a ticket:**
1. Check `./scripts/lorekeeper-backlog.sh backlog` for what's ready
2. Read the ticket file — specs live there, not in chat
3. Change `status` to `in-progress`

**Submitting work:**
1. Full test suite + lint + type check
2. Move ticket to `status: review`

## Verification Standard

Every fix or feature must have:
- **Root cause** documented in the backlog ticket (not just "fixed X")
- **Before/after evidence** — concrete scores, outputs, or test results
- **Regression test** — assert the fix can't silently regress

## Self-Testing Discipline

**The rule:** every fix needs a test that would have caught the bug. Every feature needs tests covering the happy path + at least one edge case.

**What to test:**
- Unit tests — pure functions, business logic, edge cases
- Regression tests — any bug fix must have one
- Integration tests — DB queries, service boundaries, MCP tool handlers

**Test naming pattern:**
```python
def test_<unit>_<scenario>_<expected_outcome>():
# e.g.
def test_search_unrelated_query_scores_below_threshold():
def test_lore_insert_duplicate_blocked_at_high_similarity():
def test_memory_engine_empty_store_returns_empty_list():
```

**Discipline:**
- Run `uv run pytest` locally before every push — no exceptions
- Never skip a test without a comment explaining why
- Don't mock Mem0/Chroma in memory_engine tests — real behavior only

---

## Pre-Push Self-Review Checklist

Before opening a PR, run through this:

**Correctness**
- [ ] All acceptance criteria in the ticket met?
- [ ] Edge cases handled? (null inputs, empty results, missing metadata)
- [ ] Tested manually end-to-end at least once?

**Tests**
- [ ] New logic has tests?
- [ ] Bug fix has a regression test?
- [ ] Full suite passes: `uv run pytest`?

**Code Quality**
- [ ] No debug prints / `breakpoint()` left in
- [ ] No dead code or commented-out blocks
- [ ] Linter clean: `uv run ruff check src tests`

**Documentation**
- [ ] README updated if behavior/config changed?
- [ ] Complex logic has inline comments explaining *why*, not what?

**Git**
- [ ] Commits follow `[LKPR-N] type: title` format?
- [ ] Branch named `<type>/LKPR-N-slug`?
- [ ] Ticket updated: `status: done`, `resolved_date`, root cause written?
- [ ] Ticket moved to `backlogs/done/`?

---

## PM Expectations

Things Akane (PM) will check on every review:

1. **The ticket file is updated** — root cause documented, not just `status: done`. If you found something interesting during the fix, write it down.
2. **Regression test exists** — especially for bugs. "It works now" isn't enough.
3. **No unrelated changes in the PR** — if you spot other issues, file a new ticket.
4. **Ask early if requirements are unclear** — don't build on assumptions and deliver the wrong thing.
5. **Flag scope creep immediately** — if the ticket turns out to be 3x the work, say so before diving in. PM decides: expand, split, or descope.

The bar isn't perfection — it's transparency and traceability. If something was hard, document it. If you made a judgment call, note it in the ticket or commit body.

---

## Post-Change Rule

After every set of changes:
1. Code review — check reuse, quality, efficiency
2. README consistency — verify config defaults, tool signatures, env var names still match
3. Commit with `[LKPR-N] type: title` format
4. Push to `origin` (GitHub)

## Plans Location

Implementation plans live in `docs/plans/YYYY-MM-DD_HHMMSS-<slug>.md` — **not** `.hermes/plans/`. This is the project-specific override of the global `plan` skill default.

## Skills Distribution

Skills for **Lorekeeper users/clients** live in `assets/skills/` in this repo — one folder per skill, matching the standard `skill-name/SKILL.md` structure. These are distributed to users alongside the server.

Skills for the **dev agent** (engineering practices, internal tooling) live in `.hermes/skills/` in this repo. Run `scripts/lorekeeper-setup.sh` to symlink them into `~/.hermes/skills/` so they're loadable via `skill_view`. Do NOT copy them to `assets/skills/`.