---
name: lorekeeper-dev-self-review
description: Mandatory Reflexion self-review loop for all Lorekeeper devs before pushing or opening PRs. Actor → Evaluator → Reflector cycle (max 3 iterations). Every dev must run this before git push.
version: v1.0.0
tags: [reflexion, self-review, quality-gate, pre-push]
related_skills:
  [
    lorekeeper-dev-workflow,
    lorekeeper-dev-testing,
    lorekeeper-dev-standards,
    github-pr-workflow-commits,
  ]
---

# Lorekeeper Dev — Mandatory Self-Review Loop

## When To Use

**Every time you finish an implementation and are about to push or open a PR.**

This is not optional. Every dev (Diana, future devs) must run this Reflexion loop before any `git push` or `gh pr create`. It catches issues before they reach review.

## The Reflexion Loop

```
┌──────────────────────────────────────┐
│  ACTOR: Write/fix implementation      │
│  (this is what you already do)        │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  EVALUATOR: Self-review against       │
│  criteria → score 1-10               │
└──────────────┬───────────────────────┘
               ↓ score ≥ 8?
              / \
            YES  NO
             ↓    ↓
┌────────┐  ┌──────────────────────────────┐
│ PUSH!  │  │ REFLECTOR: Diagnose failures  │
│        │  │ and generate specific fixes   │
└────────┘  └──────────────┬───────────────┘
                           ↓
              ┌──────────────────────────────┐
              │  ACTOR: Rewrite with fixes    │
              │  (iteration 2 or 3)           │
              └──────────────┬───────────────┘
                           ↓
              ┌──────────────────────────────┐
              │  EVALUATOR: re-score          │
              └──────────────────────────────┘
```

**Rules:**

- Max **3 iterations** total (Actor → Evaluator counts as 1)
- If score ≥ 8 on any iteration → push immediately
- If still < 8 after 3 iterations → **do not push**. Surface blockers to Akane/Jason with a summary of what's failing and why.

## The Evaluator Prompt (Step 2)

After writing your implementation, evaluate it against these criteria:

```
Self-Review Checklist:

1. ACCEPTANCE CRITERIA — does the implementation match every criterion
   in the ticket? List which ones are met and which (if any) are not.

2. EDGE CASES — are null, empty, duplicate, error, and boundary cases
   handled? If the input/output format changed, are callers accounted for?

3. TEST COVERAGE — do tests cover:
   - Happy path (the main success case)
   - Error path (what happens when things go wrong)
   - Edge cases (boundaries, empty inputs, duplicates)

4. CLEAN CODE — any debug prints, unused imports, dead code,
   commented-out blocks, or TODO leftovers?

5. PROJECT PATTERNS — does the code follow the established patterns
   for the specific area you're working in? (Naming, structure, style)

Score each criterion 1-10.

Output format:
- Acceptance criteria: [score] — [notes]
- Edge cases: [score] — [notes]
- Test coverage: [score] — [notes]
- Clean code: [score] — [notes]
- Project patterns: [score] — [notes]
- Overall: [score]
- Decision: [PASS if overall >= 8 / FAIL otherwise]
- Critical issues: [list, ordered by severity]
```

## The Reflector Prompt (Step 3 — only if score < 8)

Only run this if the Evaluator scored < 8. Do not skip straight to rewrite — you must reflect first.

```
Your implementation scored {score}/10.

Issues found:
{list of issues from evaluator}

For EACH issue, analyze:
1. Root cause — what logic gap or assumption led to this?
   (Don't say "I forgot to check X." Say "I assumed X was always
   present, but it can be None when Y happens.")
2. The minimal fix — what specific change is needed? Exact line or function.
3. Prevention — what would avoid this next time?

Then produce:
- Root causes: [structured analysis per issue]
- Fix plan: [ordered list of changes to make]
- Revised implementation: [the fixed code]
```

## Post-Loop Output

After the loop terminates (pass or max iterations), append this to your commit message or PR description:

```
## Self-Review
- Iterations: {N}
- Final score: {score}/10
- Issues found & fixed: {count} (list key ones)
- Self-review: PASS/FAIL
```

## Integration Points

### Into Diana's Workflow

The self-review loop fires at the end of your normal implementation flow, **before** these steps in `lorekeeper-dev-workflow`:

1. ~~Write implementation~~ (done during loop)
2. ~~Run tests~~ (done during loop)
3. Push → Open PR ← you only reach this after PASS

The `lorekeeper-dev-workflow` post-change section becomes:

```
After every set of changes:

1. Run the self-review loop (this skill) — max 3 iterations
2. If PASS → commit, push, open PR
3. If FAIL after 3 iterations → surface blockers, do not push
```

### Into Existing CI

The self-review is an agent-side gate, not a CI gate. CI continues to run `uv run pytest` and `ruff` as before. The self-review catches things before they ever reach CI.

## Reference

This is the Reflexion pattern (Shinn et al. 2023): Actor → Evaluator → Self-Reflection → repeat. On HumanEval it improved pass@1 from 80% to 91%. Adapted for Lorekeeper's development workflow.

See `~/.hermes/docs/research/agentic-loop-workflows/report.md` for the full research synthesis.
