---
id: LKPR-24
title: Migrate lorekeeper backlog to GitHub Issues
type: chore
status: proposal
priority: low
sprint: unplanned
rice_score: ~
filed_by: Hermes
filed_date: 2026-05-23
---

# [LKPR-24] Migrate lorekeeper backlog to GitHub Issues

## Problem
Current backlog is markdown files in `backlogs/` with YAML frontmatter. It works but:
- No web UI to browse/search/filter
- Can't assign tickets to people
- No PR-issue linking
- Reordering requires renaming files
- No native kanban/timeline views

## Solution
Migrate to GitHub Issues on the lorekeeper repo with:
- Labels mapped from `status` and `priority` (proposal, backlog, in-progress, review, done, critical, high, medium, low)
- Milestones for sprints
- `gh issue list` / `gh issue view` for CLI access
- Keep the local script as a complementary helper to `gh` CLI

Migration process:
1. Create labels in the repo matching current statuses + priorities
2. Migrate each ticket as a GH Issue via `gh issue create`
3. Archive old markdown files in `backlogs/archive/`
4. Update CLAUDE.md to document GH Issues workflow

## Acceptance Criteria
- [ ] All current tickets (proposal + backlog + deferred) created as GH Issues with labels
- [ ] Labels created: `proposal`, `backlog`, `in-progress`, `review`, `done`, `deferred`, `cancelled`, `critical`, `high`, `medium`, `low`
- [ ] Milestones set up for sprints
- [ ] CLAUDE.md updated to reference GH Issues workflow
- [ ] Old markdown files archived (not deleted)
- [ ] `lorekeeper-backlog.sh` updated to also check GH Issues (or retired)

## Dependencies
_None_ — pure setup change, no code impact

## Open Questions
- Keep markdown files as source of truth and sync to GH? Or GH is source of truth?
- Do we keep the local script or retire it in favor of `gh issue list`?

## Notes
Proposal from Jason (2026-05-23). Not urgent — markdown backlog is working fine. Migrate when the pain of files exceeds the effort to switch.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention