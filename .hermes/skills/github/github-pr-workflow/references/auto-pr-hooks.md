# Auto PR creation via git hooks or wrappers

Automatic PR creation is feasible, but the reliable trigger is _after the branch has been pushed_.

Preferred order:

1. post-push hook
2. wrapper command like `git publish` or `scripts/publish.sh`
3. post-commit / post-checkout helper that only checks and prompts

Avoid using pre-commit or commit-msg hooks for PR creation.

Guardrails:

- skip `main`
- check whether an open PR already exists for the branch
- do nothing if a PR already exists
- keep reviewer assignment separate from PR creation

```bash
BRANCH=$(git branch --show-current)
PR_NUMBER=$(gh pr list --head "$BRANCH" --state open --json number --jq '.[0].number // empty')

if [ -n "$BRANCH" ] && [ "$BRANCH" != "main" ] && [ -z "$PR_NUMBER" ]; then
  gh pr create \
    --base main \
    --title "[LKPR-N] type: short title" \
    --body "..."
fi
```
