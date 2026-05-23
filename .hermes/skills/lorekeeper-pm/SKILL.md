---
name: lorekeeper-pm
description: PM workflow for Lorekeeper. Load this when managing the backlog, filing tickets, reviewing dev work, or planning features. For ticket lifecycle, numbering, and script details, see the backlog-management skill.
version: 2.0.0
tags: []
related_skills: [backlog-management, lorekeeper-dev]
---

# Lorekeeper PM

Product management workflow for the Lorekeeper project.

## Roles

- **PM (Akane)** — drives product direction, files and prioritizes tickets, reviews shipped work, says yes/no on scope
- **Dev** — owns implementation, tests, and commit quality; raises blockers early; contributes to `lorekeeper-dev` skill as they learn
- **Relay** — currently Jason manually bridges PM ↔ dev (no direct channel yet). Details live in the repo; relay is for intent/clarification only.

---

## Backlog Conventions

> Full ticket lifecycle, numbering, scripts, and template → load the `backlog-management` skill.

Tickets live in `backlogs/` as `LKPR-N-slug.md`. Completed → `backlogs/done/`. Numbering: sequential (highest+1), never fill gaps.

**When filing a ticket, always separate:**
- **Backend** — services, handlers, config, tests
- **Dashboard** — UI changes in `dashboard/`. If backend-only, write `_none_` explicitly.

Dev should not have to guess whether a backend change needs a dashboard update.

**Filing a new ticket:**
1. `./scripts/lorekeeper-backlog.sh | grep "Next ticket number"` — get next LKPR-N
2. `cp backlogs/TEMPLATE.md backlogs/LKPR-NEXT-<slug>.md`
3. Include: problem statement, proposed solution, acceptance criteria
4. **File symptoms first** — if root cause is unconfirmed, label it clearly as a hypothesis
5. Commit: `[LKPR-dev] chore: add LKPR-N <short title>`

---

## Review Checklist (PM)

When dev says a ticket is done, verify:

- [ ] New commits are on `main` and pushed
- [ ] Commit message starts with `[LKPR-N]`
- [ ] Tests pass: `uv run pytest`
- [ ] Ticket file updated: `status: done`, root cause documented, `resolved_date: YYYY-MM-DD`
- [ ] Ticket moved to `backlogs/done/`
- [ ] No pre-existing test failures introduced (check full suite)

If anything is missing — send back with specific ask, don't approve partial work.

---

## Communication Protocol

1. **Specs live in the ticket file** — update the file, not just Telegram. Dev pulls main to get updates.
2. **Unclear requirement?** Dev asks → PM clarifies → ticket updated → dev proceeds. Don't build on assumptions.
3. **Scope creep during dev?** Dev flags it, PM decides: expand ticket or file a new one.
4. **Pre-existing bugs found during review?** File a new ticket, don't silently fold into current PR.

---

## Prioritization

- `critical` — blocking other work or causing data loss
- `high` — significant UX or correctness issue, next sprint
- `medium` — meaningful improvement, schedule when capacity allows
- `low` — nice to have, polish, cleanup

When in doubt: ship correctness before features.

---

## Contributing to Skills

- **Dev** should update `lorekeeper-dev` when they discover new quirks, pitfalls, or patterns
- **PM** maintains this skill (`lorekeeper-pm`) and the overall backlog structure
- Skills are in `.hermes/skills/` inside the repo — treat them like living docs, patch as you go