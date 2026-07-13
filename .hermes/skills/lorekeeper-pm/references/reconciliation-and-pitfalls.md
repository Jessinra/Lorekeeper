# Reconciliation & Datafix

Reference for `lorekeeper-pm`. Full reconciliation workflow details.

## Deep Mode (Datafix)

Full status reconciliation with per-ticket verdicts. Use when doing a manual datafix sweep:

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

## Datafix Workflow (manual)

After `--deep` reveals issues:

### 1. Change GH label

```bash
GH_TOKEN=<token> gh issue edit <num> --add-label "S:Done" --remove-label "S:Cancelled"
```

### 2. Reopen a closed issue

```bash
GH_TOKEN=<token> gh issue reopen <num>
GH_TOKEN=<token> gh issue edit <num> --add-label "S:Proposal"
```

### 3. Move backlog file between directories

Edit on the `chore/backlog` branch, move to correct directory, PR → auto-merge.

### 4. Create missing GH issue for a backlog file

```bash
GH_TOKEN=<token> gh issue create --repo Jessinra/Lorekeeper --title "LKPR-N: <title>" --label "S:Done,P2:medium" --body "$(cat backlogs/done/LKPR-N-slug.md)"
```

### 5. Duplicate resolution (manual)

Keep the open issue (usually the newer one). If the closed duplicate should be deleted: close + label S:Cancelled (no API for true deletion).

## Common Pitfalls & Lessons

### Direct commits to main

Dev committed LKPR-29 directly to main without review. Jason reset main, dev was asked to reflect. **Enforcement:** always use PR workflow. If any commit lands without a PR, revert and re-route.

### Missed cross-reference checks in reviews

LKPR-29's PR (#5) was missing two things: default score should be 5 (match `lore_insert`), and `lore_remember` wasn't recording metrics in the dashboard. Both were caught only during PM review. **Lesson:** add explicit cross-reference and dashboard checks to review.

### Analysis without execution

During mid-sprint goal shifts, PM can fall into analysis mode — producing good reasoning but stopping short of executing. Encode the workflow: present analysis → get greenlight → execute fully.

## Contributing to Skills

- **Dev** should update `lorekeeper-dev` when they discover new quirks, pitfalls, or patterns
- **PM** maintains this skill (`lorekeeper-pm`) and the overall backlog structure
- Skills are in `.hermes/skills/` inside the repo — treat them like living docs, patch as you go
