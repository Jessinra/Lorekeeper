---
id: LKPR-N
title: Short descriptive title
type: feature         # feature | bug | enhancement | research | chore
status: backlog       # proposal | backlog | in-progress | review | done | deferred | cancelled
priority: medium      # critical | high | medium | low
sprint: ~             # 1 | 2 | 3 | unplanned | deferred
rice_score: ~         # XX.X  (R:X I:X C:XX% E:Xw)  — omit if not scored
filed_by: ~           # Jason | Hermes
filed_date: YYYY-MM-DD
---

# [LKPR-N] Short descriptive title

## Problem
What's broken or missing? Describe observed symptoms — not root cause, not solution.

## Solution
What we plan to build. Concrete but not over-specified.

## Acceptance Criteria
- [ ] Criterion 1 (observable, verifiable)
- [ ] Criterion 2

## Affected Files

**Backend:**
- `path/to/file.py` — what changes

**Dashboard (if applicable):**
- `dashboard/` — describe UI change, or write `_none_` if backend-only

## Dependencies
_None_ — or list ticket IDs + reason:
- LKPR-X: must be done first because...

## Open Questions
- Question?

## Notes
Context, caveats, filing info. Mark speculative root cause clearly as unverified.
