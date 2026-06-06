---
id: LKPR-66
resolved_date: 2026-06-06
title: Markdown autoformatter — lint + format for .md files
type: chore
sprint: unplanned
rice_score: ~
filed_by: Diana
filed_date: 2026-06-05
---

# [LKPR-66] Markdown autoformatter — lint + format for .md files

## Problem

Every manually-formatted markdown table in a PR diff is a future review comment. The prompt tables in `assets/prompts/lorekeeper-agent-prompt.md` had inconsistent column widths and trailing whitespace caught in PR #138 — mechanical formatting that should never reach a human reviewer. We have autoformatters for Python (ruff) and JS (biome) but nothing for `.md` files, despite 30+ markdown files across `docs/`, `assets/prompts/`, `backlogs/`, `README.md`, etc.

Symptoms: irregular heading styles, list spacing drift, inline code fence inconsistencies, trailing whitespace, and table alignment rot.

## Solution

Selected **Prettier**.

Why:

- It actually formats markdown tables instead of only linting them.
- `proseWrap: preserve` avoids reflowing intentional hard-wrapped docs like `CLAUDE.md`.
- It fits the existing `npx`-based toolchain with no new repo-local runtime.

Implementation:

- CI runs `prettier --check` on all tracked `.md` files
- pre-commit runs the same check before commit
- a one-time `--write` pass normalized the repository markdown

## Acceptance Criteria

- [x] `--check` passes clean in CI on `.md` files
- [x] `--check` blocks pre-commit on a malformed `.md` file
- [x] All existing `.md` files normalised in one formatting commit
- [x] No content changes — formatting only (verify with `git diff --stat`)

## Affected Files

- `pyproject.toml` — optional: dev dependency if using `npm`-managed tooling
- `.githooks/pre-commit` — add format/lint step
- `.github/workflows/ci.yml` — add format/lint step
- `.prettierrc.json` — formatter config
- All `.md` files — one-time normalisation pass

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [x] Update tooling section to mention the formatter
- **README.md**: [x] Update developer tooling section with markdown formatter commands
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Notes

Filed after Jason caught table formatting issues in PR #138 and asked to ticket it separately. Previous proposal at LKPR-62 was superseded — original tool (mdformat, 778 ⭐) was too niche; this ticket scoped the two widely-adopted alternatives.
