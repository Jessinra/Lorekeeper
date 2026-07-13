# PR Workflow (curl/git fallback)

Use when `gh` is not available. For the primary `gh` workflow, see the main SKILL.md.

## Create PR (curl)

```bash
BRANCH=$(git branch --show-current)
curl -s -X POST -H "Authorization: token ***" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{
    \"title\": \"feat: add JWT-based user authentication\",
    \"body\": \"## Summary\\nCloses #42\",
    \"head\": \"$BRANCH\",
    \"base\": \"main\"
  }"
```

## Monitor CI (curl)

```bash
SHA=$(git rev-parse HEAD)
curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Overall: {d[\"state\"]}')"

# Check runs
curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/check-runs \
  | python3 -c "import sys, json; [print(f'  {r[\"name\"]}: {r[\"status\"]} / {r[\"conclusion\"] or \"pending\"}') for r in json.load(sys.stdin)['check_runs']]"
```

## Get CI Failure Details (curl)

```bash
BRANCH=$(git branch --show-current)
curl -s -H "Authorization: token ***" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?branch=$BRANCH&per_page=5" \
  | python3 -c "import sys, json; [print(f'Run {r[\"id\"]}: {r[\"name\"]} - {r[\"conclusion\"] or r[\"status\"]}') for r in json.load(sys.stdin)['workflow_runs']]"

# Get logs
curl -s -L -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/logs \
  -o /tmp/ci-logs.zip && cd /tmp && unzip -o ci-logs.zip -d ci-logs && cat ci-logs/*.txt
```

## Merge PR (curl)

```bash
curl -s -X PUT -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{\"merge_method\": \"squash\", \"commit_title\": \"feat: add user authentication (#$PR_NUMBER)\"}"

# Delete remote branch
git push origin --delete $BRANCH
git checkout main && git pull origin main
git branch -d $BRANCH
```

## Enable Auto-Merge (curl)

```bash
PR_NODE_ID=$(curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")

curl -s -X POST -H "Authorization: token ***" \
  https://api.github.com/graphql \
  -d "{\"query\": \"mutation { enablePullRequestAutoMerge(input: {pullRequestId: \\\"$PR_NODE_ID\\\", mergeMethod: SQUASH}) { clientMutationId } }\"}"
```
