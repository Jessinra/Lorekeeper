# Pre-Deployment Checklist

Every Lorekeeper PR destined for `main` must pass this before merge request is submitted.

## State Checks

- [ ] Git working tree clean (`git status --short` shows nothing)
- [ ] Branch based on latest `main` (\<= 1 commit behind origin/main)
- [ ] PR has a corresponding GitHub issue AND backlog file (`backlogs/<status>/LKPR-N-slug.md`)
- [ ] PR body has `Closes #N` or `Refs #N` referencing the correct issue number

## Code Quality

- [x] All pre-commit checks pass (ruff, bandit, biome, prettier, mcp docs, skills)
- [x] All pre-push checks pass (mypy, pip-audit, unit tests, E2E)
- [x] No hardcoded secrets, tokens, API keys in the diff
- [x] New constants use Settings with LORE\_\* env var
- [x] No magic numbers in runtime code
- [x] Banner: no print() in src/lorekeeper/ runtime code
- [x] The QA skill is in the Hermes skills dir, not assets: call `lorekeeper-qa-verification` before deploy

## Migration Safety

- [ ] `MIGRATIONS[0]` was NOT modified (bootstrap migration is immutable)
- [ ] New migration uses strictly-increasing version number
- [ ] Migration is idempotent (tested: run twice, no error)
- [ ] Enum-type migrations include ALL legacy values in the new DB CHECK constraint
- [ ] Read-side migration map exists if old values persist in DB
- [ ] Shipped skills grepped for stale type/tool references

## Testing

- [ ] New business logic has tests (happy path + ≥1 error case)
- [ ] Changes to scoring, dedup, soft-delete have regression tests
- [ ] E2E tests changed/added — run locally before PR open
- [ ] Test files pass `ruff check` (bot-authored PRs skip pre-commit)

## CI

- [ ] PR size within threshold (<500 insertions, <10 files) — warning; <1K and <20 — block
- [ ] CI green (lint-and-test + e2e)

## QA

- [ ] **QA verification run** (see `lorekeeper-qa-verification` skill) — required for any PR touching `src/lorekeeper/`
- [ ] Functional test: new types write correctly (if link types changed)
- [ ] Functional test: old types rejected at write time
- [ ] Functional test: read-side migration normalizes legacy data
- [ ] DB integrity: 0 orphan links, FK enabled, WAL mode
