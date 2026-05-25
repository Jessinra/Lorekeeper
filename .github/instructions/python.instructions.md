---
applyTo: "src/**/*.py"
---

# Python / Lorekeeper Guidelines

## Scope

Apply these rules to Python runtime code in `src/`.

## Review focus

- Prefer type-safe, mypy-friendly code.
- Keep functions small and explicit.
- Use existing project patterns instead of introducing new abstractions.
- Avoid blocking work in async paths.
- Keep exception handling visible; do not swallow errors silently.

## Project conventions

- Use `uv run ...` for tests and checks when needed.
- Keep stdout reserved for MCP protocol output.
- Use `structlog` for logging.
- Preserve data-model and schema compatibility unless a migration is included.

## Repo-specific red flags

- Any direct `print()` in runtime code is a bug unless it is intentionally part of a CLI tool.
- Swallowed exceptions or vague `except:` blocks should be treated as review issues.
- Changes to memory ranking, duplicate detection, scoring, or persistence should be reviewed as high-risk.
- If a Python change alters public behavior, confirm the README and tests still match.

## Testing expectations

- New logic should have tests in `tests/`.
- Add edge-case coverage for failures, not just happy paths.
- Prefer focused unit tests over broad integration tests unless the change needs integration coverage.

## Data and memory logic

- Be careful with duplicate detection, search ranking, confidence updates, and deletion rules.
- Treat changes to persistence or scoring as high risk.
- Verify that any migration or backfill is safe to run more than once.
