---
name: proposal-filing
description: File a new Lorekeeper proposal ticket — create markdown, create GitHub issue, commit, push. Use when requesting a new feature, filing a bug, or submitting a product idea.
version: v1.1.0
tags: []
related_skills: [backlog-management, lorekeeper-pm]
---

# Proposal Filing

Create a new Lorekeeper proposal ticket end-to-end.

## Prerequisites

- Working directory: `~/Code/lorekeeper/`
- Git identity: `git config user.name` and `user.email` must be set

## Steps

### 1. Get the next ticket number

**Always use the GitHub Issues-based script** — this works from any git state (no need to pull latest):

```bash
cd ~/Code/lorekeeper
./scripts/next-ticket-number.sh -m
```

This queries GitHub Issues for the highest existing LKPR-N and returns the next one, e.g. `LKPR-43`. Also available as machine-parseable:

```bash
./scripts/next-ticket-number.sh  # just "LKPR-43"
```

**Do NOT rely on the local git state** — you may not have the latest main branch, leading to duplicate ticket numbers.

### 2. Create the markdown file

```bash
cp backlogs/TEMPLATE.md backlogs/LKPR-N-<short-slug>.md
```

Fill in frontmatter:

```yaml
---
id: LKPR-N
title: Short descriptive title
type: feature # feature | bug | enhancement | research | chore
status: S:proposal
priority: P2:medium # P0:critical | P1:high | P2:medium | P3:low
sprint: ~
rice_score: ~
filed_by: Diana # whoever is filing
filed_date: YYYY-MM-DD
github_issue: ~ # fill after step 3
---
```

Required body sections: **Problem**, **Solution**, **Acceptance Criteria**, **Affected Files** (Backend + Dashboard or `_none_`), **Dependencies**.

### 3. Create the GitHub issue

```bash
gh issue create \
  --title "LKPR-N: <title>" \
  --label "S:Proposal,P2: medium" \
  --body "$(cat backlogs/LKPR-N-<slug>.md)" \
  --repo Jessinra/Lorekeeper
```

**Important:** GitHub label format has a space between colon and value (e.g. `P2: medium`, not `P2:medium`).

### 4. Add GitHub issue number to frontmatter

After creating the issue, add its number to the frontmatter. The pre-commit hook validates this field — it must be the numeric ID, not the full URL:

```yaml
github_issue: 211 # number only, not "https://github.com/..."
```

Then run Prettier — the pre-commit hook checks formatting and will reject unformatted files:

```bash
npx prettier --write --prose-wrap preserve backlogs/LKPR-N-<slug>.md
```

### 5. Commit the markdown file

```bash
git add backlogs/LKPR-N-<slug>.md
git commit -m "[LKPR-0] chore: add LKPR-N <short title>"
```

Use `[LKPR-0]` prefix for chores/proposals (not `[LKPR-dev]` — that's for implementation work).

### 6. Push and open a PR

Direct pushes to `main` are blocked by the pre-push hook. Always use a feature branch:

```bash
# Create a feature branch for this proposal
git checkout -b proposal/LKPR-N-<slug>

# Commit is already done in step 5, so just push
git push origin proposal/LKPR-N-<slug>
```

Then open a PR against main:

```bash
gh pr create \
  --base main \
  --head proposal/LKPR-N-<slug> \
  --title "LKPR-N: <short title>" \
  --body "Proposal ticket filed. Awaiting PM review." \
  --repo Jessinra/Lorekeeper
```

**Do not merge your own PR.** Wait for PM (Akane) or Jason to review and approve.

## Troubleshooting

- **Pre-commit hook rejects:** Two common causes:
  - Missing `github_issue` in frontmatter (fill after step 3)
  - Markdown not formatted — run `npx prettier --write --prose-wrap preserve backlogs/LKPR-N-<slug>.md`
- **Pre-push hook timed out:** The hook runs mypy + unit tests + E2E tests (~60s). Retry with a longer `timeout` parameter (300s).
- **Labels fail:** Labels are `"S:Proposal,P2: medium"` (space after colon, NOT `P2:medium`)
- **Wrong branch:** Development work goes on feature branches. Proposals go to `main` or `chore/backlog`

## Tips

- File symptoms first, not root cause — label unconfirmed hypotheses clearly
- For ideas that need research first, set `type: research` and add an Open Questions section
- Run `./scripts/next-ticket-number.sh -m` early — it queries GitHub, so no local pull needed
- If you suspect a ticket is stale/low priority, mention it in Notes — PM will triage during sprint review
