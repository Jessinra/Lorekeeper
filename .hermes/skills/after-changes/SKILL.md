---
name: after-changes
description: Post-change checklist to run after any set of code edits. Runs three steps in sequence: (1) code review via /simplify, (2) README consistency check and update, (3) git commit. Trigger on phrases like "review and commit", "after-changes", "wrap up changes", "commit my changes", or when the user says to remember to do this after every change.
version: v1.0.0
---

# After-Changes Checklist

Run these three steps in sequence after every set of code changes.

## Step 1 — Code Review

Run the `/simplify` skill. Wait for it to complete and apply all fixes before moving on.

## Step 2 — README Check

1. Run `git diff HEAD` (or `git diff HEAD~1` if already staged/committed) to get the full list of changed files and what changed.
2. Read `README.md`.
3. For each changed file, check: does the README make a claim about this file, its API, its behaviour, or its config that is now stale?
4. Common staleness patterns:
   - New env vars / config keys not in the config table
   - API endpoints added, removed, or renamed
   - New UI tabs, features, or workflows not described
   - Architecture claims that no longer match the code
   - "Cannot do X" statements that are now wrong
5. If anything is stale or missing, update `README.md` in-place. Keep changes minimal — add what's missing, fix what's wrong, remove nothing that's still true.
6. If README is already accurate, say so and skip.

## Step 3 — Commit

1. Run `git status` and `git diff HEAD` to review everything that will be committed.
2. Stage all relevant changed files (be explicit — avoid `git add -A`).
3. Write a commit message following this format:

   ```
   <type>(<scope>): <short summary under 72 chars>

   - bullet for each logical change
   - explain WHY for non-obvious changes

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   ```

   Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`

4. Confirm the commit hash and summary.

## Notes

- If Step 1 (simplify) finds and fixes issues, re-check README in Step 2 for any new staleness those fixes introduced.
- If there is nothing to commit (working tree clean), say so and stop.
- Do not push — only commit locally unless the user explicitly asks to push.
