---
id: LKPR-79
title: Layer-0 BLOCKER detection + post-merge skill learning loop
type: chore
sprint: ~
rice_score: ~
filed_by: Diana
filed_date: 2026-06-11
github_issue: 191
---

# [LKPR-79] Layer-0 BLOCKER detection + post-merge skill learning loop

## Problem

BLOCKER-tier issues (print() in src/, mem0.add() without infer=False, bare except, hardcoded secrets, SQL injection, etc.) are currently only detected at PR review stage. Review-time detection is expensive — reviewers spend attention on mechanical issues that could be caught at commit time.

Also: knowledge from review comments (patterns, anti-patterns, new BLOCKERs discovered) currently dies at merge time. No automatic feedback loop updates the skill or checklist.

## Solution

1. `scripts/check_blockers.py` — Layer-0 static BLOCKER detector (B001–B007), runs in pre-commit on staged diff only. Zero deps, <200ms.
2. `scripts/learn_from_prs.py` — Post-merge pattern extractor. Fetches recently merged PR review comments from GitHub API, classifies by severity/category, generates learning digest.
3. Hermes daily cron — calls `learn_from_prs.py`, delivers digest to Telegram, queues skill patches when new BLOCKERs are found at review stage.
4. Pre-commit hook updated to run `check_blockers.py` as the very first check.

## Acceptance Criteria

- [ ] `check_blockers.py` detects all 7 BLOCKER rules on synthetic test cases (✅ already verified)
- [ ] Pre-commit hook blocks commit on any BLOCKER finding
- [ ] `learn_from_prs.py` fetches and parses PR review comments correctly
- [ ] Daily cron delivers weekly digest to Telegram

## Affected Files

**Backend:**

- `scripts/check_blockers.py` — new Layer-0 BLOCKER detector
- `scripts/learn_from_prs.py` — new post-merge pattern extractor
- `.pre-commit-config.yaml` / pre-commit hook — updated to run check_blockers.py first
- `~/.hermes/profiles/diana/cron/jobs.json` — new daily cron entry

**Dashboard (if applicable):**

- _none_

## Dependencies

_None_

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] Update `code-review-pipeline` skill when new BLOCKERs are learned from PRs
- **Backlog**: [ ] N/A

## Open Questions

- What schedule time should the daily cron run at? (currently set to 09:00 SGT)

## Notes

GitHub issue: https://github.com/Jessinra/Lorekeeper/issues/191

Filed by Diana on 2026-06-11. check_blockers.py (B001–B007) was already verified working on synthetic test cases before this ticket was filed. The daily cron job `lorekeeper-learn-from-prs` was added to jobs.json with a `script` entry pointing at `learn_from_prs.py`, running at 09:30 SGT daily.
