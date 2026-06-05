---
id: LKPR-62
title: Markdown autoformatter (mdformat) — guard + normalise
type: chore
sprint: unplanned
rice_score: ~
filed_by: Diana
filed_date: 2026-06-05
---

# [LKPR-62] Markdown autoformatter (mdformat)

## Problem

Every manually-formatted markdown table in a PR diff is a future review comment. The prompt tables in `assets/prompts/lorekeeper-agent-prompt.md` had inconsistent column widths and trailing whitespace that Jason caught in PR #138 — but these are mechanical formatting issues that should never reach a human reviewer. We have autoformatters for Python (ruff) and JS (biome) but nothing for `.md` files, despite having 30+ markdown files across `docs/`, `assets/prompts/`, `backlogs/`, `README.md`, etc.

Symptoms pile up: irregular heading styles, list spacing drift, inline code fence inconsistencies, trailing whitespace, and table alignment rot.

## Solution

Add `mdformat` (+ `mdformat-gfm` for GitHub Flavored Markdown tables) as a pre-commit guard and CI step, matching the existing ruff/biome pattern:

- **Dev dependency:** `mdformat` + `mdformat-gfm` in `pyproject.toml`
- **Pre-commit hook:** Add `uv run mdformat --check .` after the MCP docs check (line 46 in `.githooks/pre-commit`)
- **CI:** Add the same `--check` step in `.github/workflows/ci.yml`
- **One-time normalisation:** `uv run mdformat .` on the whole repo to bring all files into compliance before the guard is active

`mdformat` is opinionated (stable output for stable input) and GFM plugin handles pipe tables correctly. `--check` mode means it's a guard, not a surprise rewrite — identical to how `ruff check` works.

## Acceptance Criteria

- [ ] `uv run mdformat --check .` passes clean in CI
- [ ] `uv run mdformat --check .` blocks pre-commit on a malformed `.md` file
- [ ] All existing `.md` files normalised in one commit
- [ ] No changes to content — formatting only (verify with `git diff --stat` after normalisation)

## Affected Files

**Backend:**

- `pyproject.toml` — add `mdformat` + `mdformat-gfm` dev deps
- `.githooks/pre-commit` — add `mdformat --check` step
- `.github/workflows/ci.yml` — add `mdformat --check` step

**All `.md` files** — one-time `mdformat .` pass

## Dependencies

*None*

## Required Updates

- **CLAUDE.md**: [ ] Update tooling section to mention mdformat
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

*None*

## Notes

Filed after Jason caught table formatting issues in PR #138 and asked to "piggy-back a ticket."