# IR-001: Docs CI Deploy Failure

**Status:** Resolved
**Severity:** Critical (production CI pipeline broken on `main`)
**Date:** 2026-06-19
**Author:** Diana
**Fix PR:** #227

---

## Summary

Deploying the documentation site via GitHub Actions failed with `fatal: empty ident name` after PR #226 was merged to `main`. The `docs` workflow could not push to the `gh-pages` branch, leaving the production docs site in a stale state.

## Timeline

| Time (UTC) | Event                                                                                 |
| ---------- | ------------------------------------------------------------------------------------- |
| ~23:30     | PR #226 ([LKPR-96] landing page production readiness) merged to `main`                |
| 23:35      | `docs` workflow triggered on main — deploy step failed                                |
| 23:53      | Diana identified root cause and applied fix on `feat/lkpr-96-landing-page-production` |
| ~23:58     | Jason requested dedicated branch: `fix/docs-ci-git-identity`                          |
| 00:00      | Fix pushed, PR #227 opened with `hot-fix` label                                       |
| 00:10      | Incident report IR-001 filed                                                          |

## Root Cause

PR #226 replaced `mkdocs gh-deploy --force` (a single MkDocs command) with a custom multi-step deploy:

1. `mkdocs build --site-dir build/docs`
2. Copy landing page assets into `build/`
3. `git init` → `git commit` → `git push`

**The bug:** `git config user.name` and `git config user.email` commands ran **before** `cd build && git init`. In a GitHub Actions `run:` block, each multi-line block is a single shell invocation, so `cd` persists — but `git config` (without `--global`) writes to the **current repo's** `.git/config`. At that point, the current repo was the checkout directory. The outer repo had an active `.git/config`, but the config was written there instead of the new deployment repo.

When `git init -b gh-pages` created a fresh repo in `build/`, and `git commit` ran inside it, there was no `user.name` / `user.email` in `build/.git/config` → `fatal: empty ident name`.

**Why it was fine before:** `mkdocs gh-deploy --force` handles git identity internally as part of its deployment logic. The previous workflow never needed explicit `git config`.

## Impact

- **Duration**: ~25 minutes between merge and fix identification
- **Scope**: `docs` workflow on `main` only; `ci.yml` (unit/E2E tests) was unaffected
- **User-facing**: The docs site was not updated — served the previous deployment
- **No data loss**: The build artifacts were correct; only the push to `gh-pages` failed

## Fix Applied

Moved the `git config` commands to execute **after** `cd build && git init -b gh-pages`, so they write identity into the deployment repo's `.git/config` instead of the outer checkout repo.

**Before (broken):**

```yaml
- name: Deploy to GitHub Pages
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    cd build
    git init -b gh-pages
    git add .
    git commit -m "..."
    git push --force ...
```

**After (fixed):**

```yaml
- name: Deploy to GitHub Pages
  run: |
    cd build
    git init -b gh-pages
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add .
    git commit -m "..."
    git push --force ...
```

## Action Items

| #   | Action                                                                                                                                                                          | Owner | Status |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------ |
| 1   | Add git config placement to CI/CD workflow review checklist — any custom git deploy step must set `user.name`/`user.email` **after** `git init` and inside the target directory | Diana | Done   |
| 2   | Create `incident-analysis` skill documenting hotfix procedure, postmortem template, and IR workflow                                                                             | Diana | Done   |
| 3   | Consider adding a `workflow_dispatch` trigger or PR-level preview deploy for landing page / docs changes so regressions are caught before hitting `main`                        | Jason | Open   |

## Lessons Learned

- Replacing a platform command (`mkdocs gh-deploy`) with manual git operations requires explicit git identity config in the correct repo context
- GitHub Actions `run:` blocks are single shell invocations — `cd` persists, but `git config` targets the **current** `.git/config`, not a future one
- First production deploy after a workflow change is the real test; add a smoke-test step or dry-run mode for future workflow PRs

## Related

- PR #226 — introduced the regression
- PR #227 — fix + this incident report
- Commit `34cc455` (original fix)
- `docs/incidents/IR-001-docs-ci-deploy.md` (this file)
