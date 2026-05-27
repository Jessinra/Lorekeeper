---
name: sprint-review
description: Sprint review workflow — triage proposals, validate ticket readiness, and batch-promote tickets to dev. Load this before running a backlog review session.
version: v1.0.0
tags: []
related_skills: [lorekeeper-pm, backlog-management]
---

# Sprint Review

Regular backlog review session to triage proposals, validate ticket readiness, and batch-promote validated tickets to dev.

## Cadence

Run a sprint review **at least weekly**, or whenever there are enough proposals to triage. The goal is to keep the dev queue healthy — not to rush work.

## Process

### 1. Review all proposals

Pull up all tickets in `S:proposal` status:

```bash
cd ~/Code/lorekeeper
./scripts/lorekeeper-backlog.sh proposal
```

For each proposal, ask:
- **Is the problem still valid?** — has anything changed since this was filed?
- **Is the solution still the right one?** — any new context that changes the approach?
- **Is the ticket complete enough?** — clear problem statement, acceptance criteria, affected files?

### 2. Validate readiness (the critical step)

**Before promoting any ticket to `S:ready`, verify:**

- [ ] **Problem still exists** — not solved by another change, not obsolete
- [ ] **Solution still makes sense** — not superseded by a better approach since filing
- [ ] **Acceptance criteria are concrete** — each AC is verifiable, not vague
- [ ] **Affected files listed** — backend paths + dashboard changes (or `_none_`)
- [ ] **No open blockers** — dependencies are listed and resolved
- [ ] **Priority still correct** — not over/under-prioritized relative to other active tickets
- [ ] **No duplicate** — check the rest of the backlog for overlapping ideas

If a ticket fails any check: update it, defer it (S:deferred), or cancel it (S:cancelled) with a note why. Don't promote stale tickets.

### 3. Triage actions

| Verdict | Action |
|---------|--------|
| ✅ Ready | Promote to `S:ready`, ensure proper `P:` priority label |
| ⏳ Needs more info | Tag as `S:deferred` with a note on what's missing |
| ❌ Not doing | Tag as `S:cancelled` with rationale |
| 📋 Merge into existing | Close as duplicate, link to parent ticket |

### 4. Batch-promote to dev

Don't promote one-off — batch all validated tickets together:

1. Update status fields in markdown files
2. Update GitHub issue labels to match
3. Commit on `chore/backlog` (with `[LKPR-0]` prefix)
4. **Rebase on main first:** `git pull origin main --rebase`
5. PR against `main` → auto-merge
6. Dev pulls `main` to see what's ready

### 5. Communicate to dev

After promoting, the dev branch should have a clean set of `S:ready` tickets. Dev's view:

```bash
./scripts/lorekeeper-backlog.sh ready    # lists S:ready tickets
gh issue list --label "S:Ready" --repo Jessinra/Lorekeeper  # same on GitHub
```

## Key Principle

**A ticket that's `S:ready` must be immediately actionable by dev.** If dev has to ask clarifying questions before starting, it's not ready — either update the ticket or keep it as proposal/deferred until it is.

This means:
- No vague ACs like "should work better" — use concrete, testable criteria
- Affected files are real paths, not guesses
- Dependencies are resolved or explicitly called out as blockers
- The ticket was updated **the day of promotion** — not stale from 2 weeks ago