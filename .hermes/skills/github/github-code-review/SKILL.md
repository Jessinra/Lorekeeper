---
name: github-code-review
description: "Review PRs: diffs, inline comments via gh or REST."
version: v1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Code-Review, Pull-Requests, Git, Quality]
    related_skills: [github-auth, github-pr-workflow]
---

# GitHub Code Review

Perform code reviews on local changes before pushing, or review open PRs on GitHub. Most of this skill uses plain `git` — the `gh`/`curl` split only matters for PR-level interactions.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repository

### Setup (for PR interactions)

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env 2>/dev/null | head -1 | cut -d= -f2 | tr -d '\n\r')
  fi
fi
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## 1. Reviewing Local Changes (Pre-Push)

### Get the Diff

```bash
git diff --staged                        # staged changes
git diff main...HEAD                     # all changes vs main
git diff main...HEAD --name-only         # file names only
git diff main...HEAD --stat              # stat summary
```

### Review Strategy

1. **Get the big picture:** `git diff main...HEAD --stat` + `git log main..HEAD --oneline`
2. **Review file by file:** `git diff main...HEAD -- path/to/file.py`
3. **Check for common issues:**
   ```bash
   git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|debugger"
   git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"
   git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="
   ```

### Review Output Format

Present findings as: **Critical** (security/correctness), **Warnings** (maintainability), **Suggestions** (style), **Looks Good** (praise).

---

## 2. Reviewing a Pull Request on GitHub

### View PR Details

```bash
gh pr view 123
gh pr diff 123
gh pr diff 123 --name-only
```

For curl/git fallbacks, see `references/review-workflow.md`.

### Check Out PR Locally

```bash
git fetch origin pull/123/head:pr-123
git checkout pr-123
# Now use read_file, search_files, run tests, etc.
git diff main...pr-123
```

### Leave Comments on a PR

```bash
gh pr comment 123 --body "Overall looks good, a few suggestions below."
```

**Inline comments:**

```bash
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')
gh api repos/$OWNER/$REPO/pulls/123/comments \
  --method POST \
  -f body="This could be simplified with a list comprehension." \
  -f path="src/auth/login.py" \
  -f commit_id="$HEAD_SHA" \
  -f line=45 \
  -f side="RIGHT"
```

### Submit a Formal Review

```bash
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
gh pr review 123 --comment --body "Some suggestions, nothing blocking."
```

---

## 3. Review Checklist

### Correctness

- Does the code do what it claims? Edge cases handled? Error paths graceful?

### Security

- No hardcoded secrets, credentials, or API keys
- Input validation on user-facing inputs
- No SQL injection, XSS, or path traversal
- SQLite DML has explicit `commit()`; background threads get separate DB connections
- Periodic job timers set **BEFORE** job (timer-after-job creates infinite retry storm)

### Code Quality

- Clear naming, no unnecessary complexity, DRY, single responsibility

### Testing

- New code paths tested? Happy path and error cases covered?

### Performance

- No N+1 queries, appropriate caching, no blocking in async code

### Documentation

- Public APIs documented, non-obvious logic explained, README updated if needed

---

## 4. Pre-Push Review Workflow

1. `git diff main...HEAD --stat` — see scope
2. `git diff main...HEAD` — read full diff
3. Use `read_file` for context on each changed file
4. Apply checklist above
5. Present findings: Critical / Warnings / Suggestions / Looks Good
6. If critical issues found, offer to fix before push

---

## 5. PR Review Workflow (End-to-End)

### Setup

```bash
source "${HERMES_HOME:-$HOME/.hermes}/skills/github/github-auth/scripts/gh-env.sh"
```

### Step 1: Gather context

```bash
gh pr view 123
gh pr diff 123 --name-only
gh pr checks 123
```

### Step 2: Check out locally

```bash
git fetch origin pull/$PR_NUMBER/head:pr-$PR_NUMBER
git checkout pr-$PR_NUMBER
```

### Step 3: Read the diff

```bash
git diff main...HEAD
git diff main...HEAD --name-only
```

### Step 4: Run automated checks

```bash
python -m pytest 2>&1 | tail -20
ruff check . 2>&1 | head -30
```

### Step 5: Apply checklist (Section 3)

### Step 6: Post review

```bash
gh pr review $PR_NUMBER --approve --body "..."
gh pr review $PR_NUMBER --request-changes --body "Found issues..."
```

### Step 7: Post summary comment

```bash
gh pr comment $PR_NUMBER --body "## Code Review Summary\n\n..."
```

> **Note:** For curl-based review submission (when `gh` is unavailable), see `references/review-workflow.md`.
