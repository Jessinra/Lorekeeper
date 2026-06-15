---
name: lorekeeper-pm
description: PM workflow for Lorekeeper. Load this when managing the backlog, filing tickets, reviewing dev work, or planning features. For ticket lifecycle, numbering, and script details, see the backlog-management skill.
version: v2.4.0
tags: []
related_skills: [backlog-management, lorekeeper-dev, sprint-review]
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

- Keep the active backlog small (max 5 tickets at a time). Push the rest to `S:proposal`.
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

## Backlog Workflow (PM)

> Full ticket lifecycle, numbering, scripts, and template → load the `backlog-management` skill.

Tickets live in `backlogs/` as `LKPR-N-slug.md`. Completed → `backlogs/done/`. Numbering: sequential (highest+1), never fill gaps.

### Weekly Planning

Once per week, pull up to **10 proposal tickets** into the active backlog:

1. Review proposals in `backlogs/proposal/` — pick high-value, unblocked items
2. Update their status to `S:ready` and set priority
3. Commit + push on the **`chore/backlog`** branch
4. Open a PR against `main` — auto-approved, no review needed
5. Jason will squash-merge it

### Mid-sprint goal shift

When Jason sets a new sprint goal mid-sprint (e.g. "lets continue with a new goal in mind":

1. **Analyze first** — map the goal to specific friction points → proposed fixes → effort estimates. Present the analysis to Jason.
2. **Get greenlight** — wait for Jason to confirm the mix before pulling into backlog.
3. **Only then, execute** — update ticket statuses to `S:ready`, move files to `backlogs/ready/` if needed, commit on `chore/backlog` branch, open PR. Don't stop after analysis.

### Filing a New Ticket

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

## GitHub Issue Integration

Since LKPR-24, status and priority are tracked via **GitHub Issue labels** — specs still live in markdown files. See `backlogs/backlog/LKPR-24-hybrid-backlog.md` for full details.

**Quick reference:**

```bash
# View active backlog on GitHub
gh issue list --label "S:Ready" --repo Jessinra/Lorekeeper

# Start work
gh issue edit LKPR-30 --add-label "S:In-progress" --remove-label "S:Ready"

# PR ready for review
gh issue edit LKPR-30 --add-label "S:Review" --remove-label "S:In-progress"

# Solved
gh issue edit LKPR-30 --add-label "S:Done" --remove-label "S:Review"

# View all done tickets this sprint
gh issue list --label "S:Done" --repo Jessinra/Lorekeeper

# Proposals
gh issue list --label "S:Proposal" --repo Jessinra/Lorekeeper
```

**Weekly sync (PM):** Pull all issue labels → update markdown `status:` fields → commit on `chore/backlog` → PR → auto-merge.

## Reconciliation (PM)

Run this to check for inconsistencies between GitHub Issues, merged PRs, and backlog markdown files. The script uses the GitHub REST API directly — no local repo clone needed. Run from the repo root.

### Standard Mode

```bash
cd /Users/jessinra/Code/lorekeeper && python3 scripts/gh_reconcile.py
```

**Checks:**

| Check                         | What it finds                                        |
| ----------------------------- | ---------------------------------------------------- |
| Merged PRs → issue not S:Done | Implementation PRs merged but ticket not marked done |
| S:Done issues still open      | Tickets labeled done but not closed                  |
| Duplicate issues              | Multiple issues with the same LKPR-N                 |
| Markdown vs GitHub mismatch   | `status:` field in .md ≠ label on GitHub issue       |
| Missing/invalid labels        | Issues missing S: or P: labels                       |

**Options:**

- `--fix-done` — auto-close issues with merged PRs
- `--fix-labels` — auto-add missing S:proposal / P3:low defaults

### Deep Mode (Datafix)

Full status reconciliation with per-ticket verdicts. Use this when doing a manual datafix sweep:

```bash
python3 ~/.hermes/scripts/gh_reconcile.py --deep
```

**Additional deep checks:**

| Deep Check                       | What it detects                                      | Common fix      |
| -------------------------------- | ---------------------------------------------------- | --------------- |
| S:Done verification              | Feature PR vs proposal PR — flags pre-PR era tickets | Verify manually |
| S:Cancelled verification         | Implemented but cancelled (#32/LKPR-7 pattern)       | → S:Done        |
| Closed S:Proposal categorization | Orphan vs duplicate vs not_planned                   | REOPEN orphans  |
| Closed S:Ready → S:Done          | Merged PRs but label not updated                     | → S:Done        |
| File location vs GH label        | File in wrong backlog directory                      | Move file       |
| Missing GH issues                | Backlog file with no corresponding issue             | Create issue    |

**Output:** A full LKPR-sorted table with the `🔴→` markers showing things that need fixing, and a summary of actions at the end.

### Datafix Workflow (manual)

After `--deep` reveals issues, here's how to apply fixes:

#### 1. Change GH label

```bash
GH_TOKEN=<token> gh issue edit <num> --add-label "S:Done" --remove-label "S:Cancelled"
GH_TOKEN=<token> gh issue edit <num> --add-label "S:Done" --remove-label "S:Ready"
```

#### 2. Reopen a closed issue

```bash
GH_TOKEN=<token> gh issue reopen <num>
GH_TOKEN=<token> gh issue edit <num> --add-label "S:Proposal"
```

#### 3. Move backlog file between directories

Edit the file on the `chore/backlog` branch, move to correct directory, PR → auto-merge.

#### 4. Create missing GH issue for a backlog file

```bash
GH_TOKEN=<token> gh issue create \
  --repo Jessinra/Lorekeeper \
  --title "LKPR-N: <title from file>" \
  --label "S:Done,P2:medium" \
  --body "$(cat backlogs/done/LKPR-N-slug.md)"
```

#### 5. Duplicate resolution (manual)

- Keep the open issue (usually the newer one with higher number)
- If the closed duplicate should be deleted: delete the issue via GitHub UI (no API for true deletion — close + label S:Cancelled is the alternative)

The script lives at `scripts/gh_reconcile.py` in the repo. Run it from the repo root:

```bash
cd /Users/jessinra/Code/lorekeeper
python3 scripts/gh_reconcile.py                # standard check
python3 scripts/gh_reconcile.py --deep         # full datafix analysis
python3 scripts/gh_reconcile.py --fix-done     # auto-close merged PR issues
python3 scripts/gh_reconcile.py --fix-labels   # auto-add missing labels
```

## Review Workflow (Dev → PM)

Dev must submit work via a **pull request** (PR) — never direct commits to `main`.

1. Dev creates a feature branch, commits with `[LKPR-N]` prefix, pushes branch
2. Dev opens a PR against `main`. PM reviews the PR on GitHub
3. PM comments inline, requests changes, or approves
4. On approval, PM **squash-merges** to main (linear history, one commit per ticket)
5. PM moves the ticket to `done`

If dev commits directly to main: revert the commits, reset main, and have dev resubmit via PR. No exceptions.

**Copilot review note:** if the repo has Copilot review instructions, use them. But do not assume `@copilot` is a valid GitHub reviewer login — request review only after verifying the repo/org supports that login, and separate reviewer assignment from PR creation so a lookup failure doesn't block the PR.

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

Priorities use `P:` prefix so GitHub labels sort correctly:

- `P0:critical` — **Only for bug & critical fixes.** Blocking other work or causing data loss.
- `P1:high` — **High impact, urgent, must do.** Significant UX or correctness issue, next sprint.
- `P2:medium` — **Medium impact, improvement, in-pipeline feature, nice to have.** Schedule when capacity allows.
- `P3:low` — **Small impact, not urgent, small improvement.** Polish, cleanup, nice-to-have.

When in doubt: ship correctness before features.

---

## Common Pitfalls & Lessons

### Direct commits to main

Dev committed LKPR-29 directly to main without review. Jason reset main, dev was asked to reflect. **Enforcement:** always use PR workflow. If any commit lands without a PR, revert and re-route.

### Missed cross-reference checks in reviews

LKPR-29's PR (#5) was missing two things: default score should be 5 (match `lore_insert`), and `lore_remember` wasn't recording metrics in the dashboard. Both were caught only during PM review on GitHub, not in the initial implementation. **Lesson:** add explicit cross-reference and dashboard checks to review (see checklist above).

### Analysis without execution

During mid-sprint goal shifts, PM can fall into analysis mode — producing good reasoning but stopping short of executing the status changes, branch, and PR. Encode the "Mid-sprint goal shift" workflow above into practice: present analysis → get greenlight → execute fully.

---

## Contributing to Skills

- **Dev** should update `lorekeeper-dev` when they discover new quirks, pitfalls, or patterns
- **PM** maintains this skill (`lorekeeper-pm`) and the overall backlog structure
- Skills are in `.hermes/skills/` inside the repo — treat them like living docs, patch as you go
