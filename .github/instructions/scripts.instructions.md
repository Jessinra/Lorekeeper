---
applyTo: "scripts/**/*.{sh,py}"
---

# Scripts Guidelines

## Scope

Apply these rules to repo scripts in `scripts/`.

## Review focus

- Scripts should be safe to rerun unless they are explicitly one-shot migrations.
- Prefer idempotent behavior and clear exit codes.
- Be careful with destructive actions: deletes, overwrites, resets, and bulk rewrites.
- Keep setup scripts and migration scripts aligned with the current repo conventions.

## Repo conventions

- `scripts/setup.sh` is the main onboarding / sync script.
- If a script installs hooks, skills, or config, make sure it still works on a fresh clone.
- If a script changes persisted data, verify there is a rollback or dry-run path when practical.
- If a script touches agent workflow, confirm it does not conflict with `CLAUDE.md`.

## Review style

- Favor explicitness over clever shell tricks.
- Flag unchecked variables, unquoted expansions, and risky `rm` / `mv` / `cp` usage.
- Prefer small helper functions over long inline command chains.
- If the script is expected to be re-run, confirm it does not duplicate work or corrupt state.
