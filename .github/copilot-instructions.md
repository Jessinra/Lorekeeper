# Lorekeeper Copilot Code Review Instructions

These instructions guide Copilot code review for this repository.

## Review priorities

- Prioritize correctness, security, data integrity, and test coverage.
- Prefer small, targeted changes over broad refactors.
- Call out missing tests, unclear behavior, and regression risk.
- If a change touches behavior, check whether docs or README need an update.

## Project context

- This repo is Python 3.11 + `uv`.
- Core checks: `uv run pytest`, `uv run ruff check src tests`, `uv run mypy src`.
- The MCP server must not write protocol output to stdout.
- Keep logging explicit; do not allow silent failures in handler or service code.

## Repo workflow conventions

- `CLAUDE.md` is the source of truth for repo-specific workflow and setup.
- Changes under `src/lorekeeper/`, `pyproject.toml`, or `loop/` may require a README consistency check.
- Prefer the smallest change that solves the problem; avoid speculative refactors.
- Treat branch / PR / commit convention violations as review issues when they affect the repo workflow.
- If the change adds behavior, settings, or a new workflow, flag whether docs or tickets should be updated too.

## What to look for

- Security issues: hardcoded secrets, unsafe input handling, auth mistakes.
- Reliability issues: swallowed exceptions, partial writes, broken cleanup, bad retries.
- Data issues: duplicate handling, score/calibration regressions, schema drift.
- Test gaps: new code paths without tests, missing edge cases, brittle assertions.
- Maintainability issues: unnecessary complexity, duplicated logic, unclear naming.

## Review style

- Be specific and actionable.
- Explain why an issue matters.
- Prefer concrete fixes over general advice.
- Acknowledge good patterns when they are genuinely present.

## Repo-specific reminders

- Changes in `src/lorekeeper/` often affect the README and should be checked against it.
- Keep public behavior stable unless the PR clearly intends a change.
- Avoid adding dependencies unless there is a strong reason.
