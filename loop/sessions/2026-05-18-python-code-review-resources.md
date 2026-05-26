---
date: 2026-05-18
topic: python-code-review-resources
task_type: review
---

## What was done

Investigated existing code review skills (`/review`, `/security-review`) and their capabilities for Python projects. Searched for authoritative external Python code review references to supplement the existing skill set.

## Decisions made

- JetBrains Qodana checklist preferred over Microsoft's for structured reference use — 10 clear categories vs. tooling-focused prose
- Deferred storage of Python review guidelines pending user decision on CLAUDE.md vs. Lorekeeper destination

## Corrections / discoveries

- `/review` skill already works on any project including Python (not Go-specific) — multi-agent, posts GitHub comment, confidence ≥80 filter
- `/security-review` exists as a separate system-level skill variant
- Google Python Style Guide surfaced as a third reference but ranked lower in utility for review checklists

## Proposed updates

- [ ] CLAUDE.md: optionally add Python code review section sourced from JetBrains + Microsoft references (pending user confirmation)
- [ ] memory: store Python review checklist categories (style, naming, SRP, immutability, Pythonic patterns, input sanitization, DRY, pre-release cleanup) with source URLs
