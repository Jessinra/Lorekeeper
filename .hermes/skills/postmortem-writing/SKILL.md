---
name: postmortem-writing
description: "Template and process for writing incident reports (IRs) with causal chain analysis, action items, and mandatory skill/checklist updates"
version: 1.0.0
author: Diana
---

# Postmortem Writing

Use this skill when authoring or reviewing an incident report (IR) for the Lorekeeper project. Every incident must produce durable process improvements — not just a fix but encoding the lesson into review patterns and checklists.

## When to Use

- A production incident occurs (P0/P1)
- A CI pipeline breaks on `main`
- A bug with systemic root cause (not a one-off typo)
- The fix changes architecture patterns, not just code

## Mandatory Deliverables

Every IR MUST deliver all of:

| #   | Deliverable                                             | Location                                           | Why                                    |
| --- | ------------------------------------------------------- | -------------------------------------------------- | -------------------------------------- |
| 1   | `docs/incidents/IR-NNN-description.md`                  | Repo `docs/incidents/`                             | Permanent record                       |
| 2   | BLOCKER pattern(s) added to `lorekeeper-code-reviewer`  | `.hermes/skills/lorekeeper-code-reviewer/SKILL.md` | Prevents same bug class passing review |
| 3   | Checklist items added to `github-code-review-checklist` | Skills directory                                   | Catches in general review too          |
| 4   | Engineering docs (if the pattern needs explanation)     | `docs/engineering/`                                | Reference for future readers           |
| 5   | Action items tracked to completion                      | IR action items table                              | Closure                                |

## IR Template

### YAML Frontmatter

```markdown
---
**Status:** [Resolved | In Progress | Monitoring]
**Severity:** [P0/P1/P2]
**Date:** YYYY-MM-DD
**Author:** [Name]
**Fix PR:** #[number]
---
```

### Sections

#### 1. Summary

One paragraph: what happened, why it was bad, what fixed it. Include the key insight in the first sentence.

#### 2. Timeline

Table of events in chronological order: time + event. Include first symptom, investigation start, fix identified, fix merged, recovery confirmed.

#### 3. Root Causes — Causal Chain

This is the most important section. Model the incident as a **chain of independent links**, where each link is survivable alone but together they create the failure.

Format each link as:

```
### 🥇 Link N: [Title]

[Technical explanation — what the link is]

**Why this caused today's crash:** [How this specific link contributed]

**Evidence:** [Log lines, metrics, code diffs, process output]
```

After the chain, show how the fixes break specific links:

```
| Fix                     | Which link it breaks | Why it suffices alone |
| ----------------------- | -------------------- | --------------------- |
| `busy_timeout=5000`     | Link 2               | ...                   |
```

#### 4. Impact

- **Duration:** [start to end — how long users were affected]
- **Scope:** [who/what was affected]
- **Data integrity:** [any data loss?]
- **User-facing:** [what users experienced]

#### 5. Detection

How the incident was first noticed (user report, alert, dashboard). Include evidence commands (e.g. `ps aux`, `curl` checks).

#### 6. Fixes Applied

Group by PR. For each PR, list changes as a table: what changed, file(s), what it does.

Separate emergency fixes (stop the bleeding) from structural fixes (eliminate the class).

#### 7. Action Items

Table: `# | Action | Owner | Status`

Every action item must be concrete and assigned. No "investigate further" — each item has a clear done condition.

**Must include:**

- Skill patches (lorekeeper-code-reviewer, github-code-review-checklist)
- Engineering docs if new pattern
- Any deferred items with explicit reason

#### 8. Lessons Learned

Numbered list of principles extracted from this incident. These go into the causal chain analysis section and become future review heuristics.

#### 9. Related

Links to: PRs, commits, related skills, engineering docs, previous IRs.

## Causal Chain Technique

The causal chain is the key insight from IR-002. Rules:

1. **Each link must be independently survivable** — if link 1 existed alone, no incident.
2. **Number links by causal proximity** — 🥇 is the first domino, 🥈 is second, etc.
3. **Provide evidence for each link** — logs, code, process output.
4. **End with a fix/chain-break table** — prove each fix independently breaks the chain.
5. **Include the dormant link** — the bug that didn't cause this incident but would cause the next one (e.g. a missing `commit()` that passed all tests).

### Chain diagram

Optionally include an ASCII causal chain diagram:

```
[Link 1 crash] ─→ [Link 2 instant error]
         │                │
         │                └──→ [User-visible symptom]
         │
         └──→ [Link 3 infinite retries] ─→ [Link 4 zombies amplify]
                                                  │
                                                  └──→ [Every init hits contention]
```

## Post-Incident Checklist

After the IR is written, verify:

- [ ] IR filed in `docs/incidents/` with sequential numbering
- [ ] BLOCKER patterns added to `lorekeeper-code-reviewer` (with concrete code examples)
- [ ] Checklist items added to `github-code-review-checklist`
- [ ] Engineering docs created/updated in `docs/engineering/`
- [ ] Action items all have owners and statuses
- [ ] Fix PRs referenced by number
- [ ] Previous IRs referenced in Related section
- [ ] Version bumped on any changed skills
