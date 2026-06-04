---
id: LKPR-24
title: Hybrid backlog — GitHub Issues for status, markdown files for specs
type: chore
sprint: 1
rice_score: ~
filed_by: Akane (PM)
filed_date: 2026-05-26
resolved_date: 2026-05-27
github_issue: 53
---

# [LKPR-24] Hybrid backlog — GitHub Issues for status, markdown files for specs

## Problem

Markdown-only backlog is friction-heavy:

- Every status change needs `git add → commit → push → PR → merge`
- No web UI to quickly glance at what's in-progress
- Can't update status from a phone

Pure GitHub Issues loses version-controlled specs and PR-reviewable ticket changes.

## Solution

**Hybrid model:**

| Concern                               | Where                                                                            | How                                                        |
| ------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------- |
| Specs (problem, solution, ACs, files) | `backlogs/LKPR-N-*.md`                                                           | Version-controlled, reviewed via PR during weekly planning |
|                                       | Status (S:proposal/S:ready/S:in-progress/S:review/S:done/S:deferred/S:cancelled) | GitHub Issue labels                                        | `gh issue edit N --add-label "S:Review"` — one command, no git            |
|                                       | Priority (P0:critical/P1:high/P2:medium/P3:low)                                  | GitHub Issue labels                                        | Same — labels visible on PR, Issues list, and web UI                      |
|                                       | Weekly sync                                                                      | `chore/backlog` branch PR                                  | Pull all issues → update markdown `status:` fields → commit → auto-merged |

## Labels Created

Updated to new naming convention:

- **Status:** `S:Proposal`, `S:Ready`, `S:In-progress`, `S:Review`, `S:Done`, `S:Deferred`, `S:Cancelled`
- **Priority:** `P0:critical`, `P1:high`, `P2:medium`, `P3:low`

`S:` and `P:` prefixes ensure labels sort correctly on GitHub.

## Migration

1. Import all existing markdown tickets as GitHub Issues with correct labels
2. Keep markdown files as-is (don't delete anything)
3. Update `lorekeeper-pm` and `lorekeeper-dev` skills with the new workflow

## Dev Workflow During Sprint

```bash
# Start working
gh issue edit LKPR-N --add-label "S:In-progress" --remove-label "S:Ready"

# PR ready
gh issue edit LKPR-N --add-label "S:Review" --remove-label "S:In-progress"

# Merged
gh issue edit LKPR-N --add-label "S:Done" --remove-label "S:Review"
```

## PM Workflow (Weekly)

```bash
# Check all ready tickets
gh issue list --label "S:Ready"

# Promote proposals to ready
gh issue edit LKPR-N --add-label "S:Ready" --remove-label "S:Proposal"

# Sync back to markdown (update status: in .md files)
# → commit on chore/backlog → PR → auto-merge
```

## Acceptance Criteria

- [x] Labels created: status (S:Proposal, S:Ready, S:In-progress, S:Review, S:Done, S:Deferred, S:Cancelled) + priority (P0:critical, P1:high, P2:medium, P3:low)
- [x] All existing tickets imported as GitHub Issues with correct labels (22 issues: #53-#74)
- [x] `lorekeeper-pm` skill updated with GitHub Issue workflow
- [x] `lorekeeper-dev` skill updated with `S:` label conventions
- [x] Markdown files remain the source of truth for specs
- [x] Read-only migration — no files deleted, no numbering changed

## Affected Files

- `backlogs/` — specs stay as markdown, no changes needed
- `.hermes/skills/lorekeeper-pm/SKILL.md` — add hybrid workflow section
- `.hermes/skills/lorekeeper-dev/SKILL.md` — update dev workflow with gh issue commands

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
