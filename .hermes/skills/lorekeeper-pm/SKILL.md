---
name: lorekeeper-pm
description: PM workflow for Lorekeeper. Load this when managing the backlog, filing tickets, reviewing dev work, or planning features. Covers ticket format, backlog conventions, review checklist, and how PM and dev collaborate.
version: 1.0.0
---

# Lorekeeper PM

Product management workflow for the Lorekeeper project.

## Roles

- **PM (Akane)** — drives product direction, files and prioritizes tickets, reviews shipped work, says yes/no on scope
- **Dev** — owns implementation, tests, and commit quality; raises blockers early; contributes to `lorekeeper-dev` skill as they learn
- **Relay** — currently Jason manually bridges PM ↔ dev (no direct channel yet). Details live in the repo; relay is for intent/clarification only.

---

## Backlog Conventions

**Location:** `backlogs/` in the repo root.

**Filename format:** `LKPR-N-short-slug.md`  
Example: `LKPR-19-fk-constraint-not-enforced.md`

**Completed tickets:** move to `backlogs/done/` — never delete.

**Template:** see `backlogs/TEMPLATE.md`

### Required frontmatter fields

```yaml
---
id: LKPR-N
title: Short descriptive title
type: bug | feature | chore | research
status: backlog | in-progress | done
priority: critical | high | medium | low
filed_by: Akane | Dev | Jason
filed_date: YYYY-MM-DD
---
```

### Filing a new ticket (PM)

1. Get the next LKPR-N by checking the highest ID in `backlogs/` and `backlogs/done/`
2. Write the file: `backlogs/LKPR-N-slug.md`
3. Include: problem statement, proposed solution, acceptance criteria, effort estimate
4. **File symptoms first** — if root cause is unconfirmed, label it clearly as a hypothesis
5. Commit: `chore(backlog): add LKPR-N <short title>`

---

## Review Checklist (PM)

When dev says a ticket is done, verify:

- [ ] New commits are on `main` and pushed
- [ ] Commit message starts with `[LKPR-N]`
- [ ] Tests pass: `uv run pytest`
- [ ] Ticket file updated: `status: done`, `resolved_date`, root cause documented
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
- Skills are in `.hermes/skills/` — treat them like living docs, patch as you go
