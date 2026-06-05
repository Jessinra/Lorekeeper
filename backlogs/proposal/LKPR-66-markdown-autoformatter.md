---
id: LKPR-66
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

Two viable options, choose one:

### Option A: Prettier (51.9k ⭐)

Industry-standard opinionated formatter. Already compatible with our toolchain — we run `npx @biomejs/biome` for JS, so `npx prettier --check` for markdown adds no new runtime. Handles GFM natively. Downside: rewrites aggressively (reflows paragraphs, normalises list indentation) — friction for docs with intentional line breaks like `CLAUDE.md`.

### Option B: markdownlint-cli2 (6.1k ⭐)

Rules-based linting with auto-fix (`--fix`), matching the ruff pattern. You control what to check (table alignment, heading style, list spacing) via config, rather than accepting an opaque reformat. Config-driven via `.markdownlint.json`. Same Node.js runtime as Option A. Battle-tested since 2015.

Both follow the existing guard pattern:

- **CI step**: `--check` mode in `.github/workflows/ci.yml`
- **Pre-commit**: add to `.githooks/pre-commit` after the existing checks
- **One-time normalisation**: format all `.md` files so the guard starts green

## Acceptance Criteria

- [ ] `--check` passes clean in CI on `.md` files
- [ ] `--check` blocks pre-commit on a malformed `.md` file
- [ ] All existing `.md` files normalised in one formatting commit
- [ ] No content changes — formatting only (verify with `git diff --stat`)

## Affected Files

- `pyproject.toml` — optional: dev dependency if using `npm`-managed tooling
- `.githooks/pre-commit` — add format/lint step
- `.github/workflows/ci.yml` — add format/lint step
- `.markdownlint.json` — config file (if Option B chosen)
- All `.md` files — one-time normalisation pass

## Dependencies

*None*

## Required Updates

- **CLAUDE.md**: [ ] Update tooling section to mention the formatter
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Which option? Prettier (zero-config, opinionated) vs markdownlint-cli2 (config-driven, lint-model, more precise control)

## Notes

Filed after Jason caught table formatting issues in PR #138 and asked to ticket it separately. Previous proposal at LKPR-62 was superseded — original tool (mdformat, 778 ⭐) was too niche; this ticket scopes the two widely-adopted alternatives.