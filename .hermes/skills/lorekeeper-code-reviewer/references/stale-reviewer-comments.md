# Stale Comments from New Reviewers on Multi-Round PRs

**Severity:** 🟡 MINOR (signal-to-noise awareness, not a code defect)

## Problem

New reviewer tools (CodeRabbit, Copilot, Sourcery) that run on a PR with prior review rounds produce stale comments. The tool sees the **final cumulated diff** — it has no awareness of:

- Intermediate commits already pushed in response to prior review rounds
- Existing reply threads resolving those same comments
- Conversation history between reviewers and the author

**Real example:** PR #247 (LKPR-101, Dashboard suggestion review tab). CodeRabbit reviewed after 2 prior Copilot review rounds (10+10 comments) were already addressed in commits `7a77d9e` and `8ee6b4b`. Of 8 new comments, **7 were stale** — already fixed in prior commits. Only 1 was actionable (SAVEPOINT atomicity for batch accept, later fixed in `bc9d7ca`).

## Triage Pattern

Before implementing **any** comment from a new reviewer on a multi-round PR:

```
1. Read the comment.
2. grep the current working tree for the code it references.
3. If the flagged code has already been changed (in a commit on the same branch):
   ⮕ Reply: "Already fixed in <commit-sha>: <what was done>. ✅"
4. If the flagged code still exists as described:
   ⮕ It's a real finding — implement the fix.
5. Check for existing reply threads on the same line — if the same issue was
   already discussed in a prior round, the comment is redundant.
```

## When to Keep the Tool Running

Even with a high stale rate (~88% in the PR #247 example), a new reviewer is worth keeping if:

- It caught **at least one real issue** that prior reviewers missed (PR #247's SAVEPOINT gap was genuine)
- It covers different signal than your primary reviewer (e.g., CodeRabbit focuses on correctness/atomicity where Copilot caught UI/JS bugs)
- It's zero-effort to run (GitHub integration) — only evaluate its output, don't gate on it

## When to Remove

Remove or disable if:

- **Every** comment across 3+ PRs is stale or false-positive — 0% actionable rate
- It generates alert fatigue that makes the team ignore all review output
- It only duplicates what the primary reviewer already flagged (identical pattern coverage)
