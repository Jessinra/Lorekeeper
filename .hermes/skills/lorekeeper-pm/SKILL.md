---
name: lorekeeper-pm
description: PM workflow for Lorekeeper. Load this when managing the backlog, filing tickets, reviewing dev work, or planning features. For ticket lifecycle, numbering, and script details, see the backlog-management skill.
version: v2.3.0
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

## Core Principles

These guide every decision — scoping, prioritization, design, review:

1. **High value, simple solutions** — every feature must justify itself. If there's a simpler way that covers 80% of the value, do that.
2. **Don't overcomplicate** — resist adding abstraction layers, new tools, or configurable options that aren't needed yet.
3. **Don't act prematurely** — if the problem isn't real (observable bug, measurable friction, explicit user ask), don't solve it. File as proposal, revisit when it hurts.
4. **Extend before create** — prefer extending existing APIs/tools/scripts over new ones. Every new MCP tool, script, or config option is debt until proven valuable.
5. **Ship correctness before features** — a working core beats an elaborate wishlist.

**Practical application — backlog hygiene:**

- Keep the active backlog small (max 5 tickets at a time). Push the rest to `proposal`.
- When scoping down a ticket, update RICE scores and note the rationale. A simpler scope that increases confidence or reduces effort means a higher RICE — reflect that.
- If a scope change eliminates an entire deliverable (e.g. dropping a new MCP tool), delete the corresponding ACs and affected files from the ticket.

---

## Commit Identity (PM)

When committing as PM (Akane), set local git identity in the repo:

```bash
git config --local user.name "Akane (PM)"
git config --local user.email "jessinra.kai@gmail.com"
```

This is enforced by the `commit-msg` hook. Load `commit-convention` skill for full details on message format, ticket tags, and examples.

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
5. Commit: `[LKPR-0] chore: add LKPR-N <short title>` (housekeeping = `[LKPR-0]`, not `[LKPR-dev]`)

---

## Review Workflow (Dev → PM)

Dev must submit work via a **pull request** (PR) — never direct commits to `main`.

1. Dev creates a feature branch, commits with `[LKPR-N]` prefix, pushes branch
2. Dev opens a PR against `main`. PM reviews the PR on GitHub
3. PM comments inline, requests changes, or approves
4. On approval, PM **squash-merges** to main (linear history, one commit per ticket)
5. PM moves the ticket to `done`

If dev commits directly to main: revert the commits, reset main, and have dev resubmit via PR. No exceptions.

## Review Checklist (PM)

When reviewing a PR:

- [ ] CI passes (lint + tests): `uv run pytest`, `uv run ruff check src tests`
- [ ] No pre-existing test failures introduced (check full suite)
- [ ] Ticket file updated: `status: review` or `status: done`, `resolved_date` if done
- [ ] **Cross-reference check:** new tool defaults match existing tool conventions (score, params, naming — e.g. `lore_remember` score must match `lore_insert`'s default of 5)
- [ ] **Dashboard check:** does the new tool need metrics tracking? Every tool should call `_increment_metric()` in the orchestrator and have a `TOOL_COLORS` entry in `dashboard/static/js/metrics.js`
- [ ] Affected Files in ticket match actual changes (no unlisted files, no phantom files)
- [ ] Required Updates in ticket are done (CLAUDE.md, README.md, skills)

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

## Common Pitfalls & Lessons

### Direct commits to main
Dev committed LKPR-29 directly to main without review. Jason reset main, dev was asked to reflect. **Enforcement:** always use PR workflow. If any commit lands without a PR, revert and re-route.

### Missed cross-reference checks in reviews
LKPR-29's PR (#5) was missing two things: default score should be 5 (match `lore_insert`), and `lore_remember` wasn't recording metrics in the dashboard. Both were caught only during PM review on GitHub, not in the initial implementation. **Lesson:** add explicit cross-reference and dashboard checks to review (see checklist above).

---

## Contributing to Skills

- **Dev** should update `lorekeeper-dev` when they discover new quirks, pitfalls, or patterns
- **PM** maintains this skill (`lorekeeper-pm`) and the overall backlog structure
- Skills are in `.hermes/skills/` inside the repo — treat them like living docs, patch as you go