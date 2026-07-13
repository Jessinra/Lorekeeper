# PR Review Workflow (curl/git fallback)

Use when `gh` is not available. For the primary `gh` workflow, see the main SKILL.md.

## View PR Details (curl)

```bash
PR_NUMBER=123
curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "
import sys, json
pr = json.load(sys.stdin)
print(f'Title: {pr[\"title\"]}')
print(f'Author: {pr[\"user\"][\"login\"]}')
print(f'Branch: {pr[\"head\"][\"ref\"]} -> {pr[\"base\"][\"ref\"]}')
print(f'State: {pr[\"state\"]}')
print(f'Body:\n{pr[\"body\"]}')"

# List changed files
curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/files \
  | python3 -c "
import sys, json
for f in json.load(sys.stdin):
    print(f'{f[\"status\"]:10} +{f[\"additions\"]:-4} -{f[\"deletions\"]:-4}  {f[\"filename\"]}')"
```

## Leave Comments (curl)

```bash
# General comment
curl -s -X POST -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/issues/$PR_NUMBER/comments \
  -d '{"body": "Overall looks good, a few suggestions below."}'

# Inline comment
HEAD_SHA=$(curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")
curl -s -X POST -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments \
  -d "{\"body\": \"Suggestion.\", \"path\": \"src/auth/login.py\", \"commit_id\": \"$HEAD_SHA\", \"line\": 45, \"side\": \"RIGHT\"}"
```

## Submit Formal Review (curl)

```bash
HEAD_SHA=$(curl -s -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")

curl -s -X POST -H "Authorization: token ***" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews \
  -d "{
    \"commit_id\": \"$HEAD_SHA\",
    \"event\": \"COMMENT\",
    \"body\": \"Code review from Hermes Agent\",
    \"comments\": [
      {\"path\": \"src/auth.py\", \"line\": 45, \"body\": \"Use parameterized queries.\"},
      {\"path\": \"src/models/user.py\", \"line\": 23, \"body\": \"Hash passwords.\"}
    ]
  }"
```

Event values: `"APPROVE"`, `"REQUEST_CHANGES"`, `"COMMENT"`
