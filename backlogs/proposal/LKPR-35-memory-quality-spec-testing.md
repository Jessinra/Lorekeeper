---
id: LKPR-35
title: Memory quality spec testing (lore_spec)
type: feature
status: S:proposal
priority: P3:low
sprint: unplanned
rice_score: ~
filed_by: Hermes (daily brainstorm)
filed_date: 2026-05-25
---

# [LKPR-35] Memory quality spec testing (lore_spec)

## Problem

No observability into whether memory extraction is working correctly. The agent stores facts all session — but there's no way to validate it stored the _right_ ones. You only notice issues when retrieval fails in production.

## Solution

Declarative memory quality tests via a YAML spec format. Each spec inserts a source statement, runs assertions against `lore_search`, and reports PASS/FAIL. Think unit tests for the memory layer.

Example:

```yaml
test-user-timezone:
  source: "I'm in Seattle, so I work PST hours"
  expect: lore_search("user timezone")[0].content ~= "PST"
    lore_search("user timezone")[0].confidence >= 7
```

Run as cron or post-session. Dashboard gets a "Memory Quality" tab.

## Acceptance Criteria

- [ ] YAML spec parser (simple key: source + expect assertions)
- [ ] Assertion runner against existing `lore_search` pipeline
- [ ] `lore_spec` tool that runs specs and returns PASS/FAIL/diff
- [ ] Dashboard tab showing quality regression over time (optional)

## Affected Files

**Backend:**

- `src/lorekeeper/tools/` — new `lore_spec` handler
- `src/lorekeeper/` — YAML parser + assertion engine

**Dashboard (if applicable):**

- `src/lorekeeper/dashboard/` — quality tab

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Should specs live in-repo (`.lorekeeper/specs/`) or alongside agent config?
- How to handle flaky tests (embedding variance, scoring jitter)?

## Notes

Filed from 2026-05-25 daily brainstorm. Low priority — high maintenance effort for ongoing value. Unlikely to be picked up soon.
