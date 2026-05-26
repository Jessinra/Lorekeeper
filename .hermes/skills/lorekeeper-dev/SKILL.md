---
name: lorekeeper-dev
description: Engineering practices for developing the Lorekeeper codebase. Load this skill when working on Lorekeeper source code, fixing bugs, adding features, writing tests, or reviewing PRs. Covers architecture conventions, SQLite/LanceDB/Chroma quirks, testing patterns, and the verification standard for shipped changes. For backlog/ticket workflow, see backlog-management skill.
version: v2.4.0
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

Engine factory: `engine_factory.py` → `build_engine()`. Orchestrator: `MemoryService` in `orchestrator.py` (was `Orchestrator` in earlier versions).

Canonical identity: `lore_id` UUID lives in the vector store's metadata. All app logic uses `lore_id`.

## Hybrid Scoring Formula

```
combined = 0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm
```

Weights are env-configurable (`LORE_W_*`). Dedup threshold: `0.6·semantic + 0.4·keyword >= 0.85`.

## Known Quirks

**Chroma distance vs. similarity (critical):**  
Mem0 v2 `score_and_rank` receives Chroma cosine _distances_ but treats them as similarities — items with distance ~0.0 get filtered out; unrelated items (distance ~1.0) score 1.0 and block all inserts.  
**Fix**: bypass mem0 pipeline — embed directly with `SentenceTransformer`, query the collection directly, return `score = 1.0 - distance`.

**LanceDB:** Always returns cosine distance (lower=better). `normalize_score()` converts to similarity: `1.0 - distance`. Probe is a no-op.

**`infer=False` on every `mem0.add()` call** — text stored verbatim, no LLM extraction.

**stdout reserved for MCP protocol** — all logging to stderr via `structlog`.

## Tooling

```bash
uv run pytest                          # run tests
uv run pytest tests/ -x -q            # fail-fast
uv run ruff check src tests            # lint (Python)
uv run ruff check src tests --fix      # auto-fix lint
uv run mypy src                        # type check (run before push; not in pre-commit hook — too slow)
npx @biomejs/biome check src/lorekeeper/dashboard/static/js/    # lint (JS)
npx @biomejs/biome check ... --write   # auto-fix JS lint
uv run lorekeeper                      # start server
```

## Pre-commit Hook

Install once per clone via `bash scripts/setup.sh`. It runs:

1. `ruff check src tests` — Python lint
2. `biome check` — JS lint
3. `uv run pytest tests/ -q` — test suite

Bypass: `git commit --no-verify` (emergency only)

See `docs/linter-decisions.md` for the full rationale on rule selection.

## Setup Script — `scripts/setup.sh`

Smart multi-agent setup. Run from the repo root:

```bash
./scripts/setup.sh
```

**What it does:**

1. Detects installed agents — Hermes (main + all profiles), Claude Code (`~/.claude`), Cursor (`~/.cursor`)
2. Injects MCP entry into each agent's config with `LORE_DATA_DIR` + `LOREKEEPER_SETUP_VERSION` env vars
3. Upserts `## Lorekeeper` section into each agent's prompt file — version-stamped, only updates when source version changes
4. Syncs skills — `assets/skills/` (copied, flat) and `.hermes/skills/` (symlinked, with category subdirs) into each agent's skills dir

**Verification after running setup.sh:**

- Hermes config contains `lorekeeper:` under `mcp_servers` with both `LORE_DATA_DIR` and `LOREKEEPER_SETUP_VERSION`
- Hermes `soul.md` (or profile `soul.md`) has a `## Lorekeeper` section with version comment matching `assets/prompts/lorekeeper-agent-prompt.md`
- `~/.hermes/skills/software-development/lorekeeper-dev` symlink exists and points into repo
- `~/.hermes/skills/` contains all user skills from `assets/skills/` (as copies, not symlinks)
- Version format on all skills: `v{M.m.m}` (with `v` prefix) — script uses string equality for idempotency

**Prompt source of truth:** `assets/prompts/lorekeeper-agent-prompt.md` — edit this to change the Lorekeeper section injected into all agents.

Re-run after editing any skill, updating the prompt file, or adding a new agent install.

## Testing Patterns

- Table-driven tests for multiple cases
- Descriptive naming: `test_search_unrelated_query_scores_below_threshold`
- Real (not mocked) vector store for memory_engine tests
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
- **never commit feature/fix/chore work directly to main** — all work goes through a feature branch → PR → merge
- **no direct pushes to main** — only PR merges land on main
- **Exception:** Akane (PM) may directly commit to main for backlog management only (ticket files, status changes, housekeeping) — never code

---

## Commit Messages

> Full convention → load the `commit-convention` skill.

Format: `[LKPR-N] type: short imperative title`

| Tag        | When                                                               |
| ---------- | ------------------------------------------------------------------ |
| `[LKPR-N]` | Work tied to a specific ticket                                     |
| `[LKPR-0]` | Housekeeping — chore, backlog edits, status changes, skill updates |

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

Examples:

```
[LKPR-6] feat: add iterative search with relevance cutoff
[LKPR-19] fix: enable FK constraints via PRAGMA foreign_keys=ON
[LKPR-0] chore: add LKPR-21 entity-resolution backlog ticket
```

Rules:

- one logical change per commit — if you need "and", split it
- never bundle unrelated changes
- no WIP commits in main — squash before merging
- **never commit directly to main** — all work goes through a feature branch → PR → merge
- **no direct pushes to main** — only PR merges land on main
- **PM exception removed:** Akane now uses the `chore/backlog` branch for backlog management, opens a PR → auto-approved → merged. No more direct pushes for anyone.
- **author name must be `Dev` or `Diana`, email `jessinra.kai@gmail.com`** — enforced by hook
  ```bash
  # Dev
  git config --local user.name "Dev"
  git config --local user.email "jessinra.kai@gmail.com"

  # Diana
  git config --local user.name "Diana"
  git config --local user.email "jessinra.kai@gmail.com"
  ```

---

## Backlog Workflow

> Full details → load the `backlog-management` skill. Brief summary below:

Tickets live in `backlogs/` as `LKPR-N-slug.md`. Completed → `backlogs/done/`. Numbering: sequential (highest+1), never fill gaps.

**Picking up a ticket:**

1. Check `./scripts/lorekeeper-backlog.sh backlog` for what's ready
2. Read the ticket file — specs live there, not in chat
3. Change `status` to `in-progress`

**Submitting work:** 3. Self-review: full test suite (`uv run pytest`) + lint (`uv run ruff check src tests`) + mypy (`uv run mypy src`) 4. Move ticket to `status: review` 5. Push branch + open PR via `gh pr create --reviewer @copilot` (load `github-pr` skill for details) 6. Ping Jason on Telegram to review and merge

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

## GitHub CLI (`gh`) — Efficient Operation

> See the `github-app-bot-auth` skill for full auth setup, token rotation, and troubleshooting.

This repo uses `jessinra-megumi-dev[bot]` for all `gh` operations. The bot auth token auto-refreshes every 45 min via cron (no manual intervention needed).

**Quick reference for common operations:**

```bash
# Check auth
gh auth status

# PR from current branch (standard flow)
git push -u origin HEAD
gh pr create --base main --title "[LKPR-N] type: title" --body "## Summary\n\nCloses LKPR-N" --reviewer @copilot

# View PR details
gh pr view 12
gh pr diff 12
gh pr checks 12

# Inline review comments (not shown by pr view)
gh api repos/Jessinra/Lorekeeper/pulls/12/comments --jq '.[] | {path, body, line}'

# Merge
gh pr merge 12 --squash --delete-branch

# General API
gh api repos/Jessinra/Lorekeeper/pulls --jq '.[] | {number, title, state}'
```

The token is short-lived (1hr) but auto-refreshed. If `gh` returns 401, run:
```bash
python3 ~/.hermes/scripts/gh-token-refresh.py
```

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
- [ ] Complex logic has inline comments explaining _why_, not what?

**Git**

- [ ] Commits follow `[LKPR-N] type: title` format (housekeeping = `[LKPR-0]`)?
- [ ] Branch named `<type>/LKPR-N-slug`?
- [ ] Ticket updated: `status: review`, `resolved_date`, root cause written?
- [ ] Pushed to `origin` and PR opened via `gh pr create --reviewer @copilot`?
- [ ] Jason pinged on Telegram to review and merge?

---

## Code Review Standards

> Apply these when reviewing PRs or self-reviewing before pushing. Flag issues at 3 levels: 🔴 **Blocker** (security/correctness), 🟡 **Should-fix** (maintainability/performance), 🟢 **Nit** (style).

### General Engineering Principles

- [ ] **Single Responsibility** — each function/class does one thing
- [ ] **DRY** — no duplicated logic; extract shared utilities
- [ ] **YAGNI** — no speculative code added "just in case"
- [ ] **PR size** — under ~400 lines; ask for splits if larger
- [ ] **No magic numbers** — literals extracted into named constants
- [ ] **Self-documenting naming** — code readable without comments
- [ ] **Max nesting depth: 3** — use early returns to flatten logic
- [ ] **No commented-out dead code** — delete it, version control has history

### Clean Code

- [ ] Functions are verbs (`get_user`, `fetch_order`), classes are nouns (`MemoryService`)
- [ ] Booleans prefixed: `is_valid`, `has_permission`, `can_retry`
- [ ] No abbreviations unless universal (`url`, `id`, `db` OK; `usrNm` ❌)
- [ ] Function length ≤ 30 lines; decompose if longer
- [ ] Comments explain _why_, not _what_
- [ ] TODOs include a ticket ref: `# TODO(LKPR-N): description`
- [ ] Errors never silently swallowed — no bare `except: pass`
- [ ] Error messages include context (what failed, what was the input)

### Python-Specific

- [ ] Type hints on all public functions (enforced by `mypy`)
- [ ] f-strings over `.format()` or `%`
- [ ] `enumerate()` over `range(len(...))`
- [ ] `zip()` for parallel iteration
- [ ] Context managers (`with`) for file/DB/network resources — never manual `.close()`
- [ ] `pathlib.Path` over `os.path` string manipulation
- [ ] Dataclasses or Pydantic models for structured data — not raw dicts
- [ ] No mutable default arguments: `def f(x=[])` ❌ → `def f(x=None)` ✅
- [ ] No bare `except:` — catch specific exceptions
- [ ] Generators for large data streams — don't load everything into RAM
- [ ] No `eval()`, `exec()`, or `pickle.loads()` on untrusted input
- [ ] SQL uses parameterized queries — never f-string into SQL
- [ ] `subprocess` calls use list args, never `shell=True` with user input

### JavaScript-Specific (dashboard code)

- [ ] `const` by default, `let` only when reassignment needed — never `var`
- [ ] `===` always — no `==` loose equality
- [ ] Destructuring for object/array access
- [ ] Optional chaining `?.` and nullish coalescing `??` used correctly
- [ ] `async/await` over raw `.then()` chains
- [ ] `Promise.all()` for parallel async — not sequential `await` in a loop
- [ ] No floating promises — all awaited or `.catch()`-handled
- [ ] No `innerHTML` with unsanitized user content (XSS risk 🔴)
- [ ] No `eval()` or `new Function()` with dynamic strings
- [ ] Event listeners cleaned up to avoid memory leaks
- [ ] `Array.at(-1)` over `arr[arr.length - 1]`

### Security (🔴 all blockers)

- [ ] No secrets in code — API keys/passwords from env vars only
- [ ] All external input validated/sanitized before use
- [ ] New `pip` or `npm` packages checked via `pip audit` / `npm audit`
- [ ] Least privilege — DB/file/API access uses minimum required permissions

### Performance

- [ ] No N+1 queries — no fetching related records in a loop
- [ ] Pagination used — no `SELECT *` or unbounded `findAll()`
- [ ] Large collections streamed/chunked, not loaded entirely into RAM
- [ ] Timeouts set on all external HTTP/DB calls — no infinite waits
- [ ] New code paths have structured logging (not `print()` / `console.log()`)

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
4. Push to `origin` (GitHub): `git push origin <branch>`
5. Open a PR and tag Copilot as reviewer — load the `github-pr` skill. In short:
   ```bash
   gh pr create --base main --title "[LKPR-N] type: title" --body "..." --reviewer @copilot
   ```
6. Ping Jason on Telegram to review and merge

## Plans Location

Implementation plans live in `docs/plans/YYYY-MM-DD_HHMMSS-<slug>.md` — **not** `.hermes/plans/`. This is the project-specific override of the global `plan` skill default.

## Skills Distribution

Skills for **Lorekeeper users/clients** live in `assets/skills/` in this repo — one folder per skill, matching the standard `skill-name/SKILL.md` structure. These are distributed to users alongside the server.

Skills for the **dev agent** (engineering practices, internal tooling) live in `.hermes/skills/` in this repo. Run `scripts/setup.sh` to symlink them into `~/.hermes/skills/` so they're loadable via `skill_view`. Do NOT copy them to `assets/skills/`.
