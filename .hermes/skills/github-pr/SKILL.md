---
name: github-pr
description: How to open a PR and request a Copilot review for the Lorekeeper repo.
version: v1.0.0
tags: []
related_skills: [lorekeeper-dev, commit-convention]
---

# GitHub PR Workflow

## Opening a PR

Use `gh pr create` to open the PR first. Requesting a reviewer is optional and can fail if the login is wrong or the repo/org doesn't expose that reviewer.

```bash
gh pr create \
  --base main \
  --title "[LKPR-N] type: short title" \
  --body "..."
```

If you want to request a reviewer, do it as a separate step after creation so a reviewer lookup failure doesn't block the PR:

```bash
gh pr edit <PR_NUMBER> --add-reviewer <reviewer-login>
```

Common pitfall: `@copilot` is not always a valid GitHub login. In some repos/orgs Copilot review is configured through repo settings rather than a user-reviewer login.

- Use `gh pr create` — not curl/REST API.
- Only request `@copilot` if you have verified that login works in this repo/org.

## Auto-create a PR for a new feature branch

If you're on a feature branch and there is no open PR for it yet, create one automatically rather than waiting for a manual step.

Recommended check:

```bash
BRANCH=$(git branch --show-current)
PR_NUMBER=$(gh pr list --head "$BRANCH" --state open --json number --jq '.[0].number // empty')

if [ -z "$PR_NUMBER" ] && [ "$BRANCH" != "main" ]; then
  gh pr create \
    --base main \
    --title "[LKPR-N] type: short title" \
    --body "..."
fi
```

Rules:

- Only do this on a real feature branch, not `main`.
- Do not create duplicate PRs if one already exists for the branch.
- If reviewer assignment is desired, do it after PR creation so a reviewer lookup failure doesn't block the PR.

## Reviewing PR comments

For PR review, `gh pr view` is not enough — it doesn't show inline review comments. Use the GitHub API when you need line-level comments.

```bash
GH_TOKEN=$(gh auth token)
curl -s -H "Authorization: Bearer $GH_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/Jessinra/Lorekeeper/pulls/<PR_NUMBER>/comments" \
  | python3 -c "import json,sys; [print(f'[{c[\"path\"]}:{c[\"line\"]}] {c[\"user\"][\"login\"]}: {c[\"body\"]}') for c in json.load(sys.stdin)]"
```

Review flow:

- `gh pr view <PR_NUMBER>` for title, body, reviewers, and status
- `gh pr diff <PR_NUMBER>` for the patch
- GitHub API `/pulls/<PR_NUMBER>/comments` for inline review comments
- If you need to act on comments, check out the branch locally and patch the files directly

Reference: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review
