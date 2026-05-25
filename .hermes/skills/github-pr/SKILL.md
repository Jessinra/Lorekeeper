---
name: github-pr
description: How to open a PR and request a Copilot review for the Lorekeeper repo.
version: v1.0.0
tags: []
related_skills: [lorekeeper-dev, commit-convention]
---

# GitHub PR Workflow

## Opening a PR

Use `gh pr create` with Copilot tagged as reviewer in one step:

```bash
gh pr create \
  --base main \
  --title "[LKPR-N] type: short title" \
  --body "..." \
  --reviewer @copilot
```

- **Always tag `@copilot` as reviewer** — every PR, no exceptions.
- Use `gh pr create` — not curl/REST API.

## Reviewing PR comments

```bash
GH_TOKEN=$(gh auth token)
curl -s -H "Authorization: Bearer $GH_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/Jessinra/Lorekeeper/pulls/<PR_NUMBER>/comments" \
  | python3 -c "import json,sys; [print(f'[{c[\"path\"]}:{c[\"line\"]}] {c[\"user\"][\"login\"]}: {c[\"body\"]}') for c in json.load(sys.stdin)]"
```

Reference: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review
