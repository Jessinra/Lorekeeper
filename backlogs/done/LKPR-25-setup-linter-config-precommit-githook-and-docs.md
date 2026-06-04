---
id: LKPR-25
github_issue: 23
title: Setup linter config, pre-commit hook, and update dev docs
type: chore
resolved_date: 2026-05-23
sprint: ~
rice_score: ~
filed_by: Jason
filed_date: 2026-05-23
---

# [LKPR-25] Setup linter config, pre-commit hook, and update dev docs

## Problem

No automated linting or testing runs on commit. Linter config is ad-hoc (Ruff defaults). No settled convention for what rules to enforce. Dev docs, skills, and CLAUDE.md don't reflect the intended workflow.

## Solution

**Phase 1 — Linter config**: Research and settle on gold-standard linter setup:

- Python: Ruff rulesets with rationale, mypy strictness level
- JS/TS: ESLint flat config or Biome (decide), Prettier if applicable
- Produce `docs/linter-decisions.md`, update `pyproject.toml`

**Phase 2 — Pre-commit hook**: Add a pre-commit hook script that runs `ruff check` + `uv run pytest`. Blocks commit on failure. Allow bypass with `--no-verify`. Installable via `scripts/lorekeeper-setup.sh`.

**Phase 3 — Docs & skills**: Update `lorekeeper-dev` skill, `CLAUDE.md`, `CONTRIBUTING.md`, `commit-convention` skill to reference the new workflow. Wire everything together.

## Acceptance Criteria

- [ ] Python: Ruff config with documented rule selections in `pyproject.toml`
- [ ] Python: mypy config with documented strictness level
- [ ] JS/TS: linter config (ESLint or Biome) decided and committed
- [ ] `docs/linter-decisions.md` — decision log with trade-offs
- [ ] Pre-commit hook runs `ruff check src tests` + `uv run pytest` before commit
- [ ] Failing lint/tests blocks the commit with clear output
- [ ] `git commit --no-verify` bypass works
- [ ] `scripts/lorekeeper-setup.sh` installs the hook
- [ ] `lorekeeper-dev` skill updated with new workflow
- [ ] `CLAUDE.md` updated
- [ ] `CONTRIBUTING.md` or README has setup instructions
- [ ] All changes committed

## Affected Files

**Backend:**

- `pyproject.toml` — Ruff + mypy settings
- `.githooks/pre-commit` — new hook script
- `scripts/lorekeeper-setup.sh` — hook installation step
- `eslint.config.js` or `biome.json` — JS/TS linter (if applicable)
- `.prettierrc` — if applicable
- `docs/linter-decisions.md` — new decision log

**Docs & Skills:**

- `CLAUDE.md` — dev workflow reference
- `lorekeeper-dev/SKILL.md` — reference hook workflow
- `commit-convention/SKILL.md` — review for consistency
- `CONTRIBUTING.md` — setup instructions

## Dependencies

_None_

## Open Questions

- Should `ruff format --check` be included in the hook, or just `ruff check`?
- Should `uv run mypy` be in the hook too? (slower — maybe optional/separate?)
- Do we have JS/TS files currently? (Dashboard HTML generator?)
- Pre-commit framework vs manual shell hook?

## Notes

Consolidated from three separate tickets after review. Single ticket, sequentially scoped phases.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
