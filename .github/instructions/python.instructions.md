---
applyTo: "**/*.{py}"
---

# Python / Lorekeeper Guidelines

## Scope

Apply these rules to Python code in `src/`, `tests/`, and `scripts/`.

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

## Testing expectations

- New logic should have tests in `tests/`.
- Add edge-case coverage for failures, not just happy paths.
- Prefer focused unit tests over broad integration tests unless the change needs integration coverage.

## Data and memory logic

- Be careful with duplicate detection, search ranking, confidence updates, and deletion rules.
- Treat changes to persistence or scoring as high risk.
- Verify that any migration or backfill is safe to run more than once.
