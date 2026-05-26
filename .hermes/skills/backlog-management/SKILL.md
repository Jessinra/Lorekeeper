---
name: backlog-management
description: Lorekeeper backlog management — ticket lifecycle, numbering, scripts, and conventions. Load this when filing tickets, moving ticket states, checking what's ready to work on, or onboarding to the project workflow.
version: v1.0.0
tags: []
related_skills: [lorekeeper-dev, lorekeeper-pm]
---

# Backlog Management

How tickets work in the Lorekeeper project. Every ticket has a lifecycle and a home.

## Where Tickets Live

```
~/Code/lorekeeper/backlogs/
├── LKPR-N-<slug>.md    # Active tickets
├── done/               # Completed tickets
└── TEMPLATE.md         # Template
```

Lorekeeper tickets (code, proposals, process, setup) → `backlogs/LKPR-N-<slug>.md`

Hermes infrastructure tickets (Docker, profiles, swarm) → `~/.hermes/backlogs/HERMES-N-<slug>.md` — NOT this repo.

## Ticket Lifecycle

```
proposal → backlog → in-progress → review → done
                         ↓
                    deferred/cancelled
```

| Status | Meaning | Who moves it |
|---|---|---|
| `proposal` | Raw idea, not yet committed | Anyone |
| `backlog` | Validated & prioritised, ready to work | PM |
| `in-progress` | Being worked on | Dev |
| `review` | Code done, pending PM review | Dev |
| `done` | Shipped, verified → moved to `backlogs/done/` | PM |
| `deferred` | Valid but not now | PM |
| `cancelled` | Won't do | PM |

## Numbering Convention

**SEQUENTIAL only.** Highest existing number + 1. Gaps are from done tickets moved to `backlogs/done/`. Never fill gaps.

Check both `backlogs/` and `backlogs/done/` to find the highest number.

## Scripts

### `lorekeeper-backlog.sh` — View tickets

```bash
cd ~/Code/lorekeeper

# All tickets grouped by status
./scripts/lorekeeper-backlog.sh

# Filter by status
./scripts/lorekeeper-backlog.sh proposal    # ideas to triage
./scripts/lorekeeper-backlog.sh backlog     # what's ready to work on
./scripts/lorekeeper-backlog.sh review      # what needs PM review
./scripts/lorekeeper-backlog.sh in-progress # what's being worked on
```

The script reads YAML frontmatter from `backlogs/*.md`, groups by status, shows priority tags, and auto-detects duplicate ticket numbers. The integrity check shows the next available ticket number.

### `lorekeeper-setup.sh` — Install repo skills

```bash
./scripts/lorekeeper-setup.sh
```

Symlinks `.hermes/skills/` from the repo into `~/.hermes/skills/`. Run once per machine, or after adding/updating any skill in `.hermes/skills/`.

## Ticket Format

Frontmatter:
```yaml
---
id: LKPR-N
title: Short descriptive title
type: bug | feature | chore | research
status: proposal | backlog | in-progress | review | done | deferred | cancelled
priority: critical | high | medium | low
filed_by: Akane | Dev | Jason
filed_date: YYYY-MM-DD
---
```

Sections: Problem, Solution, Acceptance Criteria, Affected Files (Backend + Dashboard), Dependencies, Open Questions, Notes.

For dashboard changes, list the UI component. If backend-only, write `_none_` for Dashboard.

## Discipline Rules

1. **Check backlog before starting work** → `./scripts/lorekeeper-backlog.sh backlog`
2. **When starting a ticket** → change `status` to `in-progress`
3. **When submitting for review** → change `status` to `review`
4. **When verifying done** → change `status` to `done`, add `resolved_date`, move file to `backlogs/done/`
5. **No ticket left in `in-progress` at session end** — move to `review` or revert to `backlog`
6. **Check next number before filing** → `./scripts/lorekeeper-backlog.sh | grep "Next ticket number"`
7. **File symptoms first, not speculative root cause** — label unconfirmed hypotheses clearly

## Filing a New Ticket

```bash
# 1. Check next number
./scripts/lorekeeper-backlog.sh | grep "Next ticket number"

# 2. Copy template
cp backlogs/TEMPLATE.md backlogs/LKPR-NEXT-<slug>.md

# 3. Fill it in (symptoms first, then solution)
# 4. Commit
git add backlogs/LKPR-NEXT-<slug>.md
git commit -m "[LKPR-dev] chore: add LKPR-NEXT <short title>"
```

## Pitfalls

- Don't fill gaps in numbering — sequential only
- Don't put lorekeeper management tickets in `~/.hermes/backlogs/` — they go here
- Don't guess root cause without evidence — mark it as unverified
- Don't leave `status: in-progress` across sessions without context