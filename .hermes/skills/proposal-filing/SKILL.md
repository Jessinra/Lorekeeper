---
name: proposal-filing
description: File a new Lorekeeper proposal ticket — create markdown, create GitHub issue, commit, push. Use when requesting a new feature, filing a bug, or submitting a product idea.
version: v1.0.0
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

```bash
cd ~/Code/lorekeeper
./scripts/lorekeeper-backlog.sh | grep "Next ticket number"
```

This returns `LKPR-N` — use N+1 for the new ticket.

### 2. Create the markdown file

```bash
cp backlogs/TEMPLATE.md backlogs/LKPR-N-<short-slug>.md
```

Fill in frontmatter:

```yaml
---
id: LKPR-N
title: Short descriptive title
type: feature  # feature | bug | enhancement | research | chore
status: S:proposal
priority: P2:medium  # P0:critical | P1:high | P2:medium | P3:low
sprint: ~
rice_score: ~
filed_by: Diana  # whoever is filing
filed_date: YYYY-MM-DD
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

### 4. Commit the markdown file

```bash
git add backlogs/LKPR-N-<slug>.md
git commit -m "[LKPR-0] chore: add LKPR-N <short title>"
```

Use `[LKPR-0]` prefix for chores/proposals (not `[LKPR-dev]` — that's for implementation work).

### 5. Push

```bash
git push origin main
```

Or push to `chore/backlog` if this is a PM batch:

```bash
git checkout -b chore/backlog 2>/dev/null || git checkout chore/backlog
# rebase on main first to keep PR clean:
git pull origin main --rebase
git push origin chore/backlog
```

## Troubleshooting

- **Pre-commit hook rejects:** Check frontmatter has all required fields (`sprint`, `rice_score` can be `~`)
- **Labels fail:** Labels are `"S:Proposal,P2: medium"` (space after colon, NOT `P2:medium`)
- **Wrong branch:** Development work goes on feature branches. Proposals go to `main` or `chore/backlog`

## Tips

- File symptoms first, not root cause — label unconfirmed hypotheses clearly
- For ideas that need research first, set `type: research` and add an Open Questions section
- If you suspect a ticket is stale/low priority, mention it in Notes — PM will triage during sprint review