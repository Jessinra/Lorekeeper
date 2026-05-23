# Contributing to Lorekeeper

## First-Time Setup

Run once per clone:

```bash
bash scripts/setup.sh
```

This installs:
- Python dependencies (`uv sync`)
- Git hooks (commit-msg convention + pre-commit checks)
- Hermes skills symlinks

**Prerequisites**: `uv`, `node` (for Biome JS linter)

---

## Development Workflow

### Running tests

```bash
uv run pytest              # full suite
uv run pytest tests/ -x    # stop on first failure
```

### Linting

```bash
# Python
uv run ruff check src tests
uv run ruff check src tests --fix   # auto-fix

# JavaScript (dashboard)
npx @biomejs/biome check src/lorekeeper/dashboard/static/js/
npx @biomejs/biome check src/lorekeeper/dashboard/static/js/ --write  # auto-fix

# Type check (run before pushing — not in pre-commit, too slow)
uv run mypy src
```

### Pre-commit hook

The hook installed by `setup.sh` runs ruff + biome + pytest before every commit.  
Bypass (emergency only): `git commit --no-verify`

---

## Commit Convention

Format: `[LKPR-N] type: short imperative title`

- `[LKPR-N]` — work against a specific ticket  
- `[LKPR-0]` — housekeeping (chore, backlog edits, skill updates)

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

**Author identity** (set once per clone):
```bash
git config --local user.name "Dev"
git config --local user.email "jessinra.kai@gmail.com"
```

Full details: load the `commit-convention` skill.

---

## Linter Config

See [`docs/linter-decisions.md`](docs/linter-decisions.md) for the full rationale on selected rulesets, ignored rules, and the decision between Biome and ESLint.

---

## Backlog

Tickets live in `backlogs/LKPR-N-slug.md`. Completed tickets move to `backlogs/done/`.  
See the `backlog-management` skill for the full workflow.
