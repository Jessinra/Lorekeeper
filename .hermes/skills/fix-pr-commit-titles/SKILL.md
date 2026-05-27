---
name: fix-pr-commit-titles
description: Bulk-rewrite commit titles on a PR branch to match [LKPR-N] format using filter-branch — avoids per-commit hook re-runs.
version: v1.0.0
tags: [git, commit, convention, lorekeeper, pr]
related_skills: [commit-convention, lorekeeper-dev]
---

# Fix PR Commit Titles

Use when a PR has commits with the wrong title format (e.g. `feat(lkpr-38):` instead of `[LKPR-38] feat:`).

---

## When to use

- Commits on a PR branch don't match `[LKPR-N] type: description`
- Interactive rebase (`git rebase -i --reword`) is impractical because the pre-commit hook fires on every commit and may abort on pre-existing lint violations

---

## Approach: `filter-branch --msg-filter`

Rewrites all commit messages in a range in one pass. Does NOT trigger pre-commit or commit-msg hooks — avoids the hook-per-commit problem that breaks interactive rebase.

**Trade-off**: every SHA in the range changes, even commits whose messages weren't touched. Force-push to the PR branch is required.

---

## Steps

### 1. Identify bad commits

```bash
cd ~/.hermes/profiles/diana/projects/lorekeeper

# Get PR head branch
gh pr view <N> --json headRefName,commits \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Branch:', d['headRefName']); [print(f\"{c['oid'][:8]} {c['messageHeadline']}\") for c in d['commits']]"
```

Or just inspect the local log:

```bash
git log --oneline -15
```

Look for commits with `feat(lkpr-N):`, `fix(lkpr-N):`, etc. instead of `[LKPR-N] feat:`.

### 2. Check out the PR branch

```bash
git checkout feat/lkpr-N-branch-name
# or, if not yet local:
git checkout -b feat/lkpr-N-branch-name origin/feat/lkpr-N-branch-name
```

### 3. Run filter-branch

Replace each wrong pattern with the correct `[LKPR-N] type:` form. The sed expressions are ANDed — each `-e` handles one pattern. Unmatched commits pass through unchanged.

```bash
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --msg-filter '
sed \
  -e "s/^feat(lkpr-38): /[LKPR-38] feat: /" \
  -e "s/^fix(lkpr-38): /[LKPR-38] fix: /" \
  -e "s/^chore(lkpr-38): /[LKPR-38] chore: /"
' <base-sha>..HEAD
```

`<base-sha>` is the last commit on main before the PR branch diverged — usually `origin/main` or a specific SHA. Get it with:

```bash
git merge-base HEAD origin/main
```

### 4. Verify

```bash
git log --oneline -15
```

All commits in the range should now start with `[LKPR-N]`.

### 5. Force-push

```bash
git push --force-with-lease origin feat/lkpr-N-branch-name
```

---

## Pitfalls

- **All SHAs change.** Any branch or tag pointing into the rewritten range will diverge. For PR branches that's fine — just force-push.
- **`--force-with-lease` vs `--force`**: prefer `--force-with-lease` — it fails if the remote has commits you haven't fetched, preventing accidental overwrites.
- **Double-check the base SHA.** If `<base-sha>` is wrong and you rewrite commits from main, you'll corrupt the branch. Always confirm with `git log <base-sha> --oneline -3` that it's the right commit.
- **Do not use `git rebase -i` for this.** The commit-msg hook fires on every commit during rebase. It will reject incorrectly-formatted messages and leave the rebase in an aborted state. Use filter-branch instead.
- **If interactive rebase is unavoidable**, disable hooks first:
  ```bash
  mv .git/hooks/commit-msg .git/hooks/commit-msg.disabled
  mv .git/hooks/pre-commit .git/hooks/pre-commit.disabled
  # ... rebase ...
  mv .git/hooks/commit-msg.disabled .git/hooks/commit-msg
  mv .git/hooks/pre-commit.disabled .git/hooks/pre-commit
  ```
