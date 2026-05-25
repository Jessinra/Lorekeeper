---
applyTo: "tests/**/*.py"
---

# Test Guidelines

## Scope

Apply these rules to test code in `tests/`.

## Review focus

- Tests should be deterministic and easy to diagnose when they fail.
- Prefer one behavior per test unless the grouping is very intentional.
- Cover edge cases, failure paths, and regressions — not just happy paths.
- Keep assertions specific enough to catch real regressions.

## Repo conventions

- Match the project’s current pytest style and fixture patterns.
- When production code changes behavior, add or update tests in the same area.
- If a test depends on time, randomness, or order, freeze or control it explicitly.
- If a bug was fixed, add a regression test that would have caught it.

## Review style

- Prefer clear test names that explain the behavior under test.
- Avoid overly broad fixtures or hidden setup that makes tests brittle.
- Keep test helpers small and local unless they are reused widely.
