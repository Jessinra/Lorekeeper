---
id: LKPR-56
title: TokenJuice-style compression layer for tool output
type: research # feature | bug | enhancement | research | chore
status: S:proposal # S:proposal | S:ready | S:in-progress | S:review | S:done | S:deferred | S:cancelled
priority: P3:low # P0:critical | P1:high | P2:medium | P3:low
sprint: deferred # 1 | 2 | 3 | unplanned | deferred
rice_score: ~ # XX.X  (R:X I:X C:XX% E:Xw)  — omit if not scored
filed_by: Akane # Jason | Akana | Diana
filed_date: 2026-06-02
---

# [LKPR-56] TokenJuice-style compression layer for tool output

## Problem

Tool output is where most token budget goes to die. A `git status` on a busy repo, an email thread dump, a directory listing — each can bloat context for almost no information gain. OpenHuman ships TokenJuice, a compression layer that runs on every tool result before it hits the LLM, promising up to 80% token reduction.

We have no equivalent. Every tool result flows verbatim into context.

## Solution

A configurable compression middleware that runs on tool-execution output before it reaches the model:

1. **Classify** — identify the tool/command pattern (git diff, cargo build, docker ps, ls output, etc.)
2. **Match rule** — apply the appropriate reduction strategy based on classification
3. **Reduce** — strip noise: HTML→Markdown, dedup lines, fold whitespace, truncate repeating patterns, summarize verbose sections

**Rule overlay (3 layers, later wins):**
- **Builtin** — shipped defaults for git, npm, cargo, docker, kubectl, ls, etc.
- **User** — `~/.config/tokenjuice/rules/` — personal overrides
- **Project** — `.tokenjuice/rules/` — repo-specific, checked in

Rules are simple JSON files — no recompile needed. Pattern selection per tool, reduction strategy, optional regex match/drop.

## Acceptance Criteria

- [ ] Tool output runs through compression before entering LLM context
- [ ] Builtin rules cover common tools (git, cargo, docker, ls, npm)
- [ ] User override works via `~/.config/tokenjuice/rules/`
- [ ] Measurable token reduction without information loss on tested patterns

## Affected Files

**Backend:**

- New module `src/tokenjuice/` — classifier, rules compiler, reducers, integration hooks

## Dependencies

_None_

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Where in the pipeline does this hook in? Best place is between tool execution and LLM context assembly.
- Should this be a Lorekeeper feature or a Hermes Agent feature? It's more of a general agent efficiency thing than a memory concern.
- What's the actual token savings on our usage patterns? Should measure before building.

## Notes

Inspired by OpenHuman's TokenJuice (port of vincentkoc/tokenjuice, integrated into their tool-execution path). Their implementation in Rust (`src/openhuman/tokenjuice/` — `classify.rs`, `reduce.rs`, `rules/compiler.rs`, `tool_integration.rs`). Three-layer rule overlay merged in order: builtin → user config → project config.

This is more of a general agent efficiency improvement than a memory-specific feature. Could live in Hermes core rather than Lorekeeper. Filed here for reference alongside the competitive analysis.

Strategic note: TokenJuice is a prerequisite for proactive ingestion (LKPR-55) — auto-fetching from email/chat firehoses is economically unviable without compression. But independent of that, it's a pure cost-saving measure for any agent workload.
