# Contributing to Lorekeeper

Quick guide to getting your change in without friction. Assumes you've already cloned the repo.

---

## First-time setup

```bash
git clone https://github.com/Jessinra/Lorekeeper.git
cd Lorekeeper
uv sync                    # installs all dependencies
bash scripts/setup.sh      # installs pre-commit hook + MCP config
```

That's it. The pre-commit hook blocks commits that fail lint, mypy, or tests — no surprises at PR time.

---

## The only rule: green before you commit

```bash
uv run ruff check src tests scripts/   # lint
while IFS= read -r -d '' f; do [ -f "$f" ] && printf '%s\0' "$f"; done < <(git ls-files -z '*.md') | xargs -0 npx --yes prettier@3.5.3 --check --prose-wrap preserve
uv run mypy src                         # types
uv run pytest tests/ -q                 # tests
```

All three also run in CI. If CI fails, the PR doesn't merge.

---

## Branch naming

```
feature/LKPR-<N>-<short-slug>   # new features
fix/LKPR-<N>-<short-slug>       # bug fixes
chore/LKPR-<N>-<short-slug>     # housekeeping (no behaviour change)
```

No ticket? Use `chore/LKPR-0-<slug>` for one-off housekeeping.

---

## Commit format

```
[LKPR-N] <type>: <subject>

Optional body — what changed and why.
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`

Examples:

```
[LKPR-60] feat: add cache and forget to lore_search
[LKPR-0] chore: fix ruff exclude in pyproject.toml
```

The commit-msg hook validates this format. It blocks anything that doesn't match.

---

## Ticket workflow

Tickets live in `backlogs/LKPR-<N>-<slug>.md`. Check there first before opening a GitHub issue — the backlog is the source of truth for planned work.

Opening a new ticket: use the GitHub issue template, or copy an existing backlog file.

---

## PR process

1. Push your branch
2. Open a PR — the template will prompt you for context
3. CI runs automatically (lint → mypy → tests)
4. Request review once CI is green
5. Squash-merge is preferred for clean history

PRs that touch behaviour need at least one new or updated test. Docs-only PRs are exempt.

---

## Architecture (one paragraph)

Four layers, dependencies flow downward only: **Handler** → **Service** → **Module** → **Data**. The MCP server (`server.py`) and dashboard (`dashboard/`) are both handler-layer — they call into `services/orchestrator.py` for everything. Orchestrator owns transaction boundaries. Modules own domain logic. Data layer is Chroma/LanceDB + SQLite. See `docs/ARCHITECTURE.md` for the full picture.

---

## Troubleshooting

**Pre-commit hook not running?**

```bash
bash scripts/setup.sh   # re-installs the hook
```

**Tests timing out on first run?**  
The embedding model (`all-MiniLM-L6-v2`) downloads on first use. Run `uv run pytest` once — subsequent runs hit the HF cache and are fast.

**mypy errors on `main`?**  
Unlikely — CI blocks merging with mypy errors. If you see this, open an issue.
