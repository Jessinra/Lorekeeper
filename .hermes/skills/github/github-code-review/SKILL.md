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

Perform code reviews on local changes before pushing, or review open PRs on GitHub.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repository

### Setup

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
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
git diff --staged                            # staged changes
git diff main...HEAD                         # all changes vs main
git diff main...HEAD --name-only             # file names only
git diff main...HEAD --stat                  # stat summary
```

### Review Strategy

1. **Big picture:** `git diff main...HEAD --stat` + `git log main..HEAD --oneline`
2. **File by file:** `git diff main...HEAD -- src/auth/login.py` + `read_file` for context
3. **Check for common issues:**
   ```bash
   git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|HACK\|debugger"
   git diff main...HEAD --stat | sort -t'|' -k2 -rn | head -10
   git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"
   git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="
   ```

### Review Output Format

```
## Code Review Summary
### Critical
- **src/auth.py:45** — SQL injection: use parameterized queries.
### Warnings
- **src/models/user.py:23** — Password stored in plaintext.
### Suggestions
- **src/utils/helpers.py:8** — Duplicates logic in `src/core/utils.py:34`.
### Looks Good
- Clean separation of concerns in the middleware layer
```

---

## 2. Reviewing a Pull Request on GitHub

See `references/reviewing-prs.md` for full curl/gh commands.

**Quick reference:**

```bash
# View PR
gh pr view 123
gh pr diff 123
gh pr diff 123 --name-only

# Check out locally
gh pr checkout 123
# or: git fetch origin pull/123/head:pr-123 && git checkout pr-123

# Leave inline comment
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')
gh api repos/$OWNER/$REPO/pulls/123/comments \
  --method POST \
  -f body="Your comment" \
  -f path="src/file.py" \
  -f commit_id="$HEAD_SHA" \
  -f line=45

# Submit formal review
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
```

---

## 3. Review Checklist

### Correctness

- Does the code do what it claims? Edge cases handled? Error paths handled gracefully?

### Security

- No hardcoded secrets, credentials, or API keys
- Input validation on user-facing inputs
- No SQL injection, XSS, or path traversal
- SQLite DML has explicit `commit()`
- Background threads get separate DB connections
- Periodic job timers set BEFORE job

### Code Quality

- Clear naming, no unnecessary complexity, DRY, single responsibility

### Testing

- New code paths tested? Happy path and error cases covered?

### Performance

- No N+1 queries, appropriate caching, no blocking in async code

### Documentation

- Public APIs documented, non-obvious logic has comments, README updated

---

## 4. Pre-Push Review Workflow

When asked to "review the code" or "check before pushing":

1. `git diff main...HEAD --stat` — see scope
2. `git diff main...HEAD` — read full diff
3. `read_file` for each changed file if needed
4. Apply the checklist above
5. Present findings in structured format (Critical / Warnings / Suggestions / Looks Good)
6. If critical issues found, offer to fix before push

---

## 5. PR Review Workflow (End-to-End)

See `references/pr-review-workflow.md` for the full 9-step workflow.

**Key steps:**

1. Set up environment → 2. Gather PR context → 3. Check out locally → 4. Read diff → 5. Run automated checks → 6. Apply checklist → 7. Post review → 8. Summary comment → 9. Clean up

**Pitfalls:**

- Reviewer assignment can fail if login is wrong — create PR first, then request reviewer
- `@copilot` is not always a valid GitHub login
- Inline comments are line-sensitive and must target the current head commit
- Always refresh from `origin/main` first before reviewing
