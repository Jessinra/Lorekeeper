# PR Review Workflow — End-to-End (Full Reference)

## Step 1: Set up environment

```bash
source "${HERMES_HOME:-$HOME/.hermes}/skills/github/github-auth/scripts/gh-env.sh"
```

## Step 2: Gather PR context

```bash
# With gh
gh pr view 123
gh pr diff 123 --name-only
gh pr checks 123

# With curl
PR_NUMBER=123
curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$GH_OWNER/$GH_REPO/pulls/$PR_NUMBER
curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$GH_OWNER/$GH_REPO/pulls/$PR_NUMBER/files
```

## Step 3: Check out the PR locally

```bash
git fetch origin pull/$PR_NUMBER/head:pr-$PR_NUMBER
git checkout pr-$PR_NUMBER
```

## Step 4: Read the diff

```bash
git diff main...HEAD
git diff main...HEAD --name-only
git diff main...HEAD -- path/to/file.py
```

## Step 5: Run automated checks

```bash
python -m pytest 2>&1 | tail -20
ruff check . 2>&1 | head -30
```

## Step 6: Apply review checklist (see SKILL.md Section 3)

## Step 7: Post the review

```bash
# Approve
gh pr review $PR_NUMBER --approve --body "Reviewed by Hermes Agent."
# Request changes
gh pr review $PR_NUMBER --request-changes --body "Found issues — see inline comments."
# Comment
gh pr review $PR_NUMBER --comment --body "Some suggestions."
```

Atomic curl review:

```bash
HEAD_SHA=$(curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$GH_OWNER/$GH_REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")

curl -s -X POST \
  -H "Authorization: token ***" \
  https://api.github.com/repos/$GH_OWNER/$GH_REPO/pulls/$PR_NUMBER/reviews \
  -d "{
    \"commit_id\": \"$HEAD_SHA\",
    \"event\": \"REQUEST_CHANGES\",
    \"body\": \"## Hermes Agent Review\n\nFound 2 issues, 1 suggestion.\",
    \"comments\": [
      {\"path\": \"src/auth.py\", \"line\": 45, \"body\": \"🔴 Critical: SQL injection.\"},
      {\"path\": \"src/models.py\", \"line\": 23, \"body\": \"⚠️ Plaintext password.\"},
      {\"path\": \"src/utils.py\", \"line\": 8, \"body\": \"💡 Duplicated logic.\"}
    ]
  }"
```

## Step 8: Post summary comment

```bash
gh pr comment $PR_NUMBER --body "$(cat <<'EOF'
## Code Review Summary
**Verdict: Changes Requested** (2 issues, 1 suggestion)

### 🔴 Critical
- **src/auth.py:45** — SQL injection vulnerability

### ⚠️ Warnings
- **src/models.py:23** — Plaintext password storage

### 💡 Suggestions
- **src/utils.py:8** — Duplicated logic, consider consolidating

### ✅ Looks Good
- Clean API design
- Good error handling
EOF
)"
```

## Step 9: Clean up

```bash
git checkout main
git branch -D pr-$PR_NUMBER
```

## Decision Guide

- **Approve** — no critical or warning-level issues
- **Request Changes** — any critical or warning-level issue that should be fixed before merge
- **Comment** — observations and suggestions, nothing blocking (draft or uncertain PRs)
