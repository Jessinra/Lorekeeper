---
id: LKPR-46
title: Daily Memory Digest — a human pull loop
type: feature
status: S:proposal
priority: P3:low
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 88
filed_date: 2026-05-28
---

# [LKPR-46] Daily Memory Digest — a human pull loop

## Problem

The daily reflect loop is agent-only. A human who isn't running Hermes agents has zero daily reason to touch Lorekeeper. No pull, no habit loop, no "come back" mechanism. The tool stays open in the background, forgotten.

## Solution

A scheduled cron job that generates a daily "memory digest":
- Compact summary of what happened in the last 24h
- New memories created (count + highlights)
- Top-accessed memories
- "Memory of the Day" — highest-scored new entry
- Nudge for low-confidence memories that need human review ("3 memories may be stale — review with `lore_check`")
- Deliver via cron output (stdout → delivery channel of choice), or optional email/slack hook

Reuses existing reflect infrastructure for the aggregation logic.

## Acceptance Criteria

- [ ] User receives a daily digest with new memory count, top accesses, and Memory of the Day
- [ ] Low-confidence memory nudges are surfaced in the digest
- [ ] Reuses existing reflect/aggregation code where possible
- [ ] Compatible with cron delivery (no new infrastructure needed)

## Affected Files

**Backend:**

- `scripts/daily_digest.py` — new aggregation/digest generator
- `services/` — minor refactors to expose reflect data

**Dashboard (if applicable):**

_none_ — cron-driven, no UI

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [ ] Update if digest script becomes a recommended cron setup
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Format: Email vs slack vs cron stdout? Start with cron delivery, extend later.
- Should this be a built-in cronjob (bundled) or a recipe in docs? Start with docs + template, bundle if adoption justifies it.

## Notes

Originated from lorekeeper-daily-ideas cronjob (2026-05-28). Jason likes the idea but has no immediate use case — filed as P3 for now. No direct use case yet but good future value.