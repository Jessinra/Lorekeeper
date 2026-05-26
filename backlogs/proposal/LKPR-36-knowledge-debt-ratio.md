---
id: LKPR-36
title: Knowledge debt ratio (lore_debt)
type: feature
status: S:proposal
priority: P3:low
sprint: unplanned
rice_score: ~
filed_by: Hermes (daily brainstorm)
filed_date: 2026-05-25
---

# [LKPR-36] Knowledge debt ratio (lore_debt)

## Problem

Memory fills with noise over time — transient commands, trivial chatter, false starts. There's no signal-to-noise metric, so you can't tell how much of the graph is junk. Decay handles _old_ noise but not _low-value_ noise.

## Solution

Every memory gets a derived `knowledge_debt` score — the probability it's noise based on low confidence × low usefulness × zero re-access. Aggregate to a system debt ratio.

Expose as:

- `lore_debt` — returns the ratio + breakdown by topic
- `lore_prune(debt_threshold=0.7, dry_run=True)` — shows what would be purged
- Dashboard gets a "Debt" panel with green/yellow/red gauge

Complements the decay model (ages by time) with value-based garbage collection. A 2-day-old memory with high confidence and recurring usefulness keeps full weight. A 2-hour-old trivium with low confidence and never-reaccessed gets flagged immediately.

## Acceptance Criteria

- [ ] Debt scored as derived metric from existing confidence + usefulness + `usage_count`
- [ ] `lore_debt` tool returns ratio and per-topic breakdown
- [ ] `lore_prune` tool with `dry_run=True` showing purge candidates
- [ ] Dashboard debt panel (optional, deferred)

## Affected Files

**Backend:**

- `src/lorekeeper/tools/` — new `lore_debt` + `lore_prune` handlers
- `src/lorekeeper/` — debt scoring logic (derived, no schema migration)

**Dashboard (if applicable):**

- `src/lorekeeper/dashboard/` — debt panel

## Dependencies

_None_ — reuses existing confidence + usefulness + usage_count fields

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- What's the right debt formula? `(1 - confidence) × (1 - usefulness) × exp(-usage_count)`?
- Dry-run threshold for prune — should it be configurable per-session?

## Notes

Filed from 2026-05-25 daily brainstorm. Low priority — high maintenance effort for ongoing value. Unlikely to be picked up soon.
