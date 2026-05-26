---
id: LKPR-24
title: Hybrid backlog — GitHub Issues for status, markdown files for specs
type: chore
status: backlog
priority: high
sprint: 1
rice_score: ~
filed_by: Akane (PM)
filed_date: 2026-05-26
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

| Concern | Where | How |
|---------|-------|-----|
| Specs (problem, solution, ACs, files) | `backlogs/LKPR-N-*.md` | Version-controlled, reviewed via PR during weekly planning |
| Status (proposal/backlog/in-progress/review/done) | GitHub Issue labels | `gh issue edit N --add-label "done"` — one command, no git |
| Priority (critical/high/medium/low) | GitHub Issue labels | Same — labels visible on PR, Issues list, and web UI |
| Weekly sync | `chore/backlog` branch PR | Pull all issues → update markdown `status:` fields → commit → auto-merged |

## Labels Created

Already done — labels exist in the repo:
- **Status:** `proposal`, `backlog`, `in-progress`, `review`, `done`, `deferred`, `cancelled`
- **Priority:** `critical`, `high`, `medium`, `low`

## Migration

1. Import all existing markdown tickets as GitHub Issues with correct labels
2. Keep markdown files as-is (don't delete anything)
3. Update `lorekeeper-pm` and `lorekeeper-dev` skills with the new workflow

## Dev Workflow During Sprint

```bash
# Start working
gh issue edit LKPR-N --add-label "in-progress"

# PR ready
gh issue edit LKPR-N --add-label "review"

# Merged
gh issue edit LKPR-N --add-label "done"
```

## PM Workflow (Weekly)

```bash
# Check all open issues
gh issue list --label backlog

# Promote proposals to backlog
gh issue edit LKPR-N --add-label "backlog" --remove-label "proposal"

# Sync back to markdown (update status: in .md files)
# → commit on chore/backlog → PR → auto-merge
```

## Acceptance Criteria

- [x] Labels created: status (proposal, backlog, in-progress, review, done, deferred, cancelled) + priority (critical, high, medium, low)
- [ ] All existing tickets imported as GitHub Issues with correct labels
- [ ] `lorekeeper-pm` and `lorekeeper-dev` skills updated with hybrid workflow
- [ ] Markdown files remain the source of truth for specs
- [ ] Read-only migration — no files deleted, no numbering changed

## Affected Files

- `backlogs/` — specs stay as markdown, no changes needed
- `.hermes/skills/lorekeeper-pm/SKILL.md` — add hybrid workflow section
- `.hermes/skills/lorekeeper-dev/SKILL.md` — update dev workflow with gh issue commands