---
id: LKPR-71
title: README marketing pass — branding, screenshots, use-cases, benchmark results
type: chore
status: S:Proposal
priority: P1:high
sprint: beta
rice_score: ~
filed_by: PM (Akane)
filed_date: 2026-06-08
github_issue: 164
---

## Problem

The README was rewritten for clarity (LKPR-57) but it's still text-only. No screenshots, no demo, no benchmark evidence. For someone landing on the repo for the first time, there's no visual proof it works or why they should install it. The positioning manifesto defines our brand tone but the README doesn't consistently reflect it yet.

## Solution

Four-phase README marketing pass:

### Phase 1 — Brand tone audit

- Read through the positioning manifesto (`docs/positioning-manifesto.md`)
- Tighten README hero/header to reflect the pitch consistently
- Core tagline: "Memory for AI agents that gets smarter the more you use it — no cloud, no config"
- Remove any hype language that doesn't match manifesto values (zero friction, local-first, honest about trade-offs)

### Phase 2 — Visual proof

- Add dashboard screenshot (Memories tab with populated data, png)
- Add search results screenshot showing hybrid matching
- Add comparison table screenshot or polish the existing markdown table
- Add terminal recording / GIF of `pip install lorekeeper-mcp` → first memory → search (30s demo)
- All screenshots go in `docs/screenshots/` with naming convention `screenshot-<purpose>.png`

### Phase 3 — Use-case section

Add concrete "when would you use this" scenarios:

- **Agent session continuity** — agent remembers user preferences across sessions
- **Project onboarding** — clone repo, run setup, agent instantly knows the codebase
- **Cross-session awareness** — "remember the deployment fix from last week"
- **Multi-agent sharing** — different agents (Claude Code, Codex, Gemini) share one memory pool

### Phase 4 — Benchmark results

- Once LKPR-70 produces real numbers, embed the results in a "Why it matters" section
- Context token savings table (most compelling chart from agentmemory's benchmarks)
- Search latency at scale
- Comparison vs built-in memory (CLAUDE.md / grep)

## Acceptance Criteria

- [ ] Phase 1: Brand tone audit applied — hero section matches positioning manifesto
- [ ] Phase 2: At least 2 dashboard screenshots + 1 demo GIF committed
- [ ] Phase 2: Screenshots in `docs/screenshots/` with consistent naming
- [ ] Phase 3: Use-case section with 4+ concrete scenarios
- [ ] Phase 4: Benchmark results section populated from LKPR-70 output (once available)
- [ ] Comparison table polished and visually scannable
- [ ] README is scannable in < 30s — hero, screenshot, use-case, quickstart, benchmark

## Affected Files

- `README.md` — main target
- `docs/screenshots/` — new directory, 2-3 images + 1 GIF
- `docs/positioning-manifesto.md` — already exists, reference only

## Dependencies

- Phase 4 blocks on LKPR-70 (benchmark script) producing real numbers
- Everything else is independent

## Required Updates

- [ ] Skills: [ ] None needed
