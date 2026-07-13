---
name: github-pr-workflow
description: "GitHub PR lifecycle: branch, commit, open, CI, merge."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge]
    related_skills: [github-auth, github-code-review]
---

# GitHub Pull Request Workflow

Complete guide for managing the PR lifecycle. All sections show the `gh` way — for `git` + `curl` fallbacks, see `references/curl-fallback.md`.

## Diverged Branch Recovery

```bash
git log --oneline origin/main..HEAD   # local-only commits
git log --oneline HEAD..origin/main   # remote-only commits
git add -A && git stash
git pull --rebase
git stash pop
```

Prefer `--rebase` over `--no-rebase` — keeps history linear.

## Prerequisites

### Quick Auth Detection

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
fi
echo "Using: $AUTH"
```

### Extracting Owner/Repo

```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## 1. Branch Creation

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b feat/add-user-authentication
```

Branch naming: `feat/`, `fix/`, `refactor/`, `docs/`, `ci/` + description.

## 2. Making Commits

```bash
git add src/auth.py src/models/user.py
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add unit tests for auth flow"
```

Commit format: `type(scope): short description`. Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`.

## 3. Pushing and Opening a PR

### Push

```bash
git push -u origin HEAD
```

### Create the PR

```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "## Summary\nCloses #42"
```

Options: `--draft`, `--reviewer user1,user2`, `--label "enhancement"`, `--base develop`

**Pitfall — requesting a reviewer can fail the create:** `@copilot` is not always a valid GitHub login. Create the PR first, then add reviewer separately:

```bash
gh pr edit <PR_NUMBER> --add-reviewer <reviewer-login>
```

For curl fallback, see `references/curl-fallback.md`.

## 4. Monitoring CI Status

```bash
gh pr checks
gh pr checks --watch   # polls every 10s
```

## 5. Auto-Fixing CI Failures

### Step 1: Get Failure Details

```bash
gh run list --branch $(git branch --show-current) --limit 5
gh run view <RUN_ID> --log-failed
```

### Step 2: Fix and Push

```bash
git add <fixed_files>
git commit -m "fix: resolve CI failure in <check_name>"
git push
```

### Auto-Fix Loop

1. Check CI → identify failures
2. Read logs → understand error
3. Fix code with `patch`/`write_file`
4. `git add . && git commit -m "fix: ..." && git push`
5. Wait for CI → re-check
6. Repeat up to 3 attempts, then ask user

## 6. Resolving PR Review Feedback

### Never amend+force-push after PR is open

- Each fix = a new plain commit (`git commit -m "fix: ..."` + `git push`)
- Amend + force-push blows away inline comment anchors

### Step 1: Find Inline Comments

```bash
PR_NUMBER=8
gh api repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments \
  --jq '.[] | {path, body, line, commit_id}'
```

### Step 2: Make Changes on the Feature Branch

```bash
git add <changed_files>
git commit -m "[TICKET-N] fix: address PR review feedback"
git push
```

### Step 3: Verify

```bash
gh pr view $PR_NUMBER --json state,headRefOid
```

## 7. Merging

```bash
# Squash merge + delete branch
gh pr merge --squash --delete-branch

# Enable auto-merge
gh pr merge --auto --squash --delete-branch
```

## 8. Complete Workflow Example

```bash
# 1. Start from clean main
git checkout main && git pull origin main

# 2. Branch
git checkout -b fix/login-redirect-bug

# 3. (Agent makes code changes with file tools)

# 4. Commit
git add src/auth/login.py tests/test_login.py
git commit -m "fix: correct redirect URL after login"

# 5. Push
git push -u origin HEAD

# 6. Create PR (see Section 3)

# 7. Monitor CI (see Section 4)

# 8. Merge when green (see Section 7)
```
