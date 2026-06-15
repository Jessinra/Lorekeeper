---
name: backlog-management
description: Lorekeeper backlog management — ticket lifecycle, numbering, scripts, and conventions. Load this when filing tickets, moving ticket states, checking what's ready to work on, or onboarding to the project workflow.
version: v1.1.0
tags: []
related_skills: [lorekeeper-dev, lorekeeper-pm]
---

# Backlog Management

How tickets work in the Lorekeeper project. Every ticket has a lifecycle and a home.

## Where Tickets Live

```
~/Code/lorekeeper/backlogs/
├── proposal/           # Raw ideas, S:Proposal
├── ready/              # Validated + prioritized, S:Ready
├── done/               # Shipped + verified, S:Done
├── cancelled/          # Won't do, S:Cancelled
└── TEMPLATE.md         # Template
```

Tickets are PROPOSAL → READY → DONE (or CANCELLED). **File location must match status** — when status changes, `git mv` the file to the corresponding subdirectory. Zero files should live at `backlogs/` root level.

**Currently deferred** tickets (S:Deferred) remain in `proposal/` with the deferred label; they aren't ready for promotion but aren't dead either. Cancelled tickets are never reborn.

## Ticket Lifecycle

```
S:proposal → S:ready → S:in-progress → S:review → S:done
                         ↓
               S:deferred / S:cancelled
```

| Status          | Meaning                                | Who moves it | File location |
| --------------- | -------------------------------------- | ------------ | ------------- |
| `S:proposal`    | Raw idea, not yet committed            | Anyone       | `proposal/`   |
| `S:ready`       | Validated & prioritised, ready to work | PM           | `ready/`      |
| `S:in-progress` | Being worked on                        | Dev          | `ready/`      |
| `S:review`      | Code done, pending PM review           | Dev          | `ready/`      |
| `S:done`        | Shipped, verified                      | PM           | `done/`       |
| `S:deferred`    | Valid but not now                      | PM           | `proposal/`   |
| `S:cancelled`   | Won't do                               | PM           | `cancelled/`  |

## Numbering Convention

**SEQUENTIAL only.** Highest existing number + 1. Gaps are from done tickets moved to `backlogs/done/`. Never fill gaps.

Check all subdirectories (`proposal/`, `ready/`, `done/`, `cancelled/`) to find the highest number.

## Frontmatter Convention

Each file has a YAML frontmatter with metadata. The `github_issue` field is **mandatory** and enforced by the pre-commit hook:

```yaml
---
id: LKPR-N
title: Short descriptive title
type: bug | feature | enhancement | research | chore
status: S:Proposal
priority: P2:medium # P0:critical | P1:high | P2:medium | P3:low
sprint: ~
rice_score: ~
filed_by: Akane | Diana | Jason
filed_date: YYYY-MM-DD
github_issue: 123 # REQUIRED — pre-commit hook validates this
---
```

**Status and priority must stay in sync between file frontmatter and GitHub labels.** Both are sources of truth. When promoting a ticket (e.g. proposal → ready), update BOTH:

1. File: change `status: S:Proposal` → `S:Ready`, `git mv` to new subdirectory
2. GitHub: `gh issue edit N --add-label "S:Ready" --remove-label "S:Proposal"`

The daily backlog triage cron job (`lorekeeper-daily-backlog-triage`) checks for drift between file status and GH labels and reports mismatches.

Sections: Problem, Solution, Acceptance Criteria, Affected Files (Backend + Dashboard), Dependencies, Open Questions, Notes.

For dashboard changes, list the UI component. If backend-only, write `_none_` for Dashboard.

## Scripts

### `lorekeeper-backlog.sh` — View tickets

```bash
cd ~/Code/lorekeeper
./scripts/lorekeeper-backlog.sh
./scripts/lorekeeper-backlog.sh proposal
./scripts/lorekeeper-backlog.sh backlog
```

### `next-ticket-number.sh` — Get the next available number

```bash
./scripts/next-ticket-number.sh
./scripts/next-ticket-number.sh -m  # machine-parseable
```

Uses GitHub Issues API — authoritative regardless of which branch you're on.

## Promoting a Ticket (Proposal → Ready)

```bash
cd ~/Code/lorekeeper
git mv backlogs/proposal/LKPR-N-<slug>.md backlogs/ready/
# Edit status: S:Proposal → S:Ready
npx prettier --write --prose-wrap preserve backlogs/ready/LKPR-N-<slug>.md
gh issue edit N --add-label "S:Ready" --remove-label "S:Proposal"
git add backlogs/ready/LKPR-N-<slug>.md
git commit -m "[LKPR-0] chore: promote LKPR-N to ready"
```

## Closing a Ticket (Done)

```bash
cd ~/Code/lorekeeper
git mv backlogs/ready/LKPR-N-<slug>.md backlogs/done/
# Edit status: S:Ready → S:Done
gh issue close N
git add backlogs/done/LKPR-N-<slug>.md
git commit -m "[LKPR-0] chore: close LKPR-N (shipped)"
```

## Reconciling Backlog Drift

When files and GitHub issues have drifted:

1. **Audit**: Compare file frontmatter vs GH labels for every ticket
2. **File location**: Ensure file is in correct subdirectory matching its status
3. **Status sync**: Update file `status:` to match GH label
4. **Title collision**: If GH title claims wrong LKPR-N vs body `id:`, fix the title
5. **Missing `github_issue`**: Add the field — pre-commit validates it
6. **Root-level files**: Move to appropriate subdirectory
7. **Duplicate files**: Remove the copy in wrong directory, keep the correct one

## Filing a New Ticket

```bash
# 1. Get next number
./scripts/next-ticket-number.sh
# 2. Copy template
cp backlogs/TEMPLATE.md backlogs/proposal/LKPR-NEXT-<slug>.md
# 3. Fill in, create GH issue, add github_issue to frontmatter
# 4. npx prettier --write --prose-wrap preserve
# 5. Commit on proposal branch
```

## Pitfalls

- Don't fill gaps in numbering — sequential only
- Don't leave `status: in-progress` across sessions without context
- File-GH label drift is common — the daily triage cron catches it
- When creating a file from an existing GH issue body, check for title/number collisions first
- Pre-commit hook validates: `github_issue`, prettier, ticket prefix
- Use `git push --no-verify` to bypass pre-push hook only on proposal branches, never main
