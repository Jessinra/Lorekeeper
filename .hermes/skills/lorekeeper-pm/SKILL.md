---
name: lorekeeper-pm
description: "PM workflow for Lorekeeper. Load when managing backlog, filing tickets, reviewing dev work, or planning features. For ticket lifecycle, numbering, and scripts, see backlog-management skill."
version: v2.4.1
tags: []
related_skills: [backlog-management, lorekeeper-dev, sprint-review]
---

# Lorekeeper PM

Product management workflow for the Lorekeeper project.

## Roles

- **PM (Akane)** — drives product direction, files and prioritizes tickets, reviews shipped work, says yes/no on scope
- **Dev** — owns implementation, tests, and commit quality; raises blockers early; contributes to `lorekeeper-dev`
- **Relay** — Jason manually bridges PM ↔ dev. Repo holds details; relay is for intent/clarification only.

## Core Principles

1. **High value, simple solutions** — if a simpler way covers 80% of the value, do that.
2. **Don't overcomplicate** — resist abstraction layers, new tools, or configurable options not needed yet.
3. **Don't act prematurely** — if the problem isn't real (observable bug, measurable friction), don't solve it. File as proposal.
4. **Extend before create** — prefer extending existing APIs/tools/scripts over new ones.
5. **Ship correctness before features** — a working core beats an elaborate wishlist.

**Backlog hygiene:** Keep active backlog small (max 5 tickets). Push rest to `S:proposal`. When scoping down, update RICE scores and note rationale.

## Commit Identity (PM)

```bash
git config --local user.name "Akane (PM)"
git config --local user.email "jessinra.kai@gmail.com"
```

Enforced by `commit-msg` hook. See `commit-convention` skill for full details.

## Backlog Workflow

> Full ticket lifecycle, numbering, scripts → load `backlog-management` skill.

Tickets live in `backlogs/` as `LKPR-N-slug.md`. Completed → `backlogs/done/`. Numbering: sequential (highest+1), never fill gaps.

### Weekly Planning

Once per week, pull up to **10 proposal tickets** into active backlog:

1. Review proposals in `backlogs/proposal/` — pick high-value, unblocked items
2. Update status to `S:ready`, set priority. Commit on `chore/backlog` branch
3. Open PR against `main` — auto-approved, no review needed. Jason squash-merges.

### Mid-sprint goal shift

When Jason sets a new goal mid-sprint: 1) Analyze → map friction to fixes → estimates. 2) Get greenlight. 3) Execute: update statuses, commit on `chore/backlog`, PR.

### Filing a New Ticket

1. `./scripts/lorekeeper-backlog.sh | grep "Next ticket number"` — get next LKPR-N
2. `cp backlogs/TEMPLATE.md backlogs/LKPR-NEXT-<slug>.md`
3. Include: problem, solution, acceptance criteria. File symptoms first.
4. Commit: `[LKPR-0] chore: add LKPR-N <short title>`

## GitHub Issue Integration

Status and priority tracked via GitHub Issue labels. Specs in markdown files.

```bash
gh issue list --label "S:Ready" --repo Jessinra/Lorekeeper
gh issue edit LKPR-30 --add-label "S:In-progress" --remove-label "S:Ready"
```

**Weekly sync:** Pull all issue labels → update markdown status fields → commit on `chore/backlog` → PR → auto-merge.

## Reconciliation (PM)

Run from repo root: `python3 scripts/gh_reconcile.py`

**Checks:** Merged PRs not marked S:Done, S:Done issues still open, duplicate issues, markdown vs GitHub label mismatch, missing/invalid labels. Options: `--fix-done`, `--fix-labels`, `--deep`.

See `references/reconciliation-and-pitfalls.md` for full deep mode, datafix workflow, and common pitfalls.

## Review Workflow (Dev → PM)

Dev submits via PR — never direct commits to main. PM reviews on GitHub, comments inline, approves or requests changes. PM squash-merges on approval, moves ticket to done.

## Review Checklist (PM)

- [ ] CI passes (lint + tests): `uv run pytest`, `uv run ruff check src tests`
- [ ] No pre-existing test failures introduced
- [ ] Ticket file updated: `status: review/done`, `resolved_date` if done
- [ ] Cross-reference check: new tool defaults match existing conventions
- [ ] Dashboard check: does the new tool need metrics tracking?
- [ ] Affected Files in ticket match actual changes
- [ ] Required Updates in ticket are done (CLAUDE.md, README.md, skills)

If anything missing — send back with specific ask.

## Communication Protocol

1. Specs live in the ticket file — update the file, not just Telegram.
2. Unclear requirement? Dev asks → PM clarifies → ticket updated → dev proceeds.
3. Scope creep during dev? Dev flags, PM decides: expand ticket or file new one.
4. Pre-existing bugs found during review? File new ticket, don't fold into current PR.

## Prioritization

- `P0:critical` — Blocking other work or data loss. Only for bug & critical fixes.
- `P1:high` — High impact, urgent. Next sprint.
- `P2:medium` — Medium impact, improvement. When capacity allows.
- `P3:low` — Small impact, polish. Nice-to-have.

## References

- `references/reconciliation-and-pitfalls.md` — Full deep mode, datafix workflow, and historical lessons
