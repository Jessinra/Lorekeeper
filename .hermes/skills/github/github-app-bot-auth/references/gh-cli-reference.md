# gh CLI Reference

## PR Lifecycle

```bash
# Create a PR from current branch
gh pr create --base main --title "[LKPR-N] type: title" --body "## Summary\n\nChanges:\n- ...\n\nCloses LKPR-N"

# Create a PR with Copilot reviewer
gh pr create --base main --title "[LKPR-N] type: title" --body "..." --reviewer @copilot

# View PR details
gh pr view 12                          # specific PR number
gh pr view --json title,body,state     # raw JSON fields

# Get the PR diff for review
gh pr diff 12

# List open PRs
gh pr list --author @me
gh pr list --state open --limit 10

# Check CI/checks status
gh pr checks 12
gh pr checks 12 --watch                # poll until complete

# Merge (squash preferred)
gh pr merge 12 --squash --delete-branch
gh pr merge 12 --auto --squash         # enable auto-merge

# Add a comment
gh pr comment 12 --body "Addressed in latest push"

# Close without merging
gh pr close 12
```

## Reading Inline Review Comments

```bash
gh api repos/Jessinra/Lorekeeper/pulls/12/comments --jq '.[] | {path, body, line}'
```

## GitHub API Calls

```bash
# GET requests
gh api repos/Jessinra/Lorekeeper                         # repo info
gh api repos/Jessinra/Lorekeeper/pulls                    # list PRs
gh api repos/Jessinra/Lorekeeper/issues                   # list issues
gh api repos/Jessinra/Lorekeeper/contents/CLAUDE.md       # file content

# POST/PATCH requests
gh api repos/Jessinra/Lorekeeper/pulls -X POST -f title="..." -f head=branch -f base=main
gh api repos/Jessinra/Lorekeeper/issues/1/comments -X POST -f body="..."

# Filter with jq
gh api repos/Jessinra/Lorekeeper/pulls --jq '.[] | {number, title, state, created_at}'
gh api repos/Jessinra/Lorekeeper/pulls/12 --jq '.head.ref'

# Pagination
gh api repos/Jessinra/Lorekeeper/pulls --paginate --jq '.[].title'
```

## Working with the Lorekeeper Repo

```bash
git branch --show-current
git log --oneline -5
git diff main...HEAD --stat
git push -u origin HEAD && gh pr create --base main --title "[LKPR-N] type: title" --body "..."
gh pr view --json url --jq '.url'
git log --oneline origin/main..HEAD
git log --oneline HEAD..origin/main
```
