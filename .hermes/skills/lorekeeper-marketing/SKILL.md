---
name: lorekeeper-marketing
description: >
  Marketing workflow for Lorekeeper — README copy, manifesto, positioning, and multi-agent
  A/B testing of copy variations. Load this when working on any user-facing content: README,
  docs/manifesto.md, positioning, comparison tables, or launch copy.
version: v1.0.0
tags: [marketing, readme, positioning, ab-testing]
related_skills: [lorekeeper-pm, deep-research]
---

# Lorekeeper Marketing

User-facing content workflow for the Lorekeeper project.

---

## Core Principles

All Lorekeeper marketing copy must follow these non-negotiables:

1. **Don't burn bridges** — tech ecosystems thrive when there's a lot of contribution from open
   source and adoption. Never undermine competing tools. Acknowledge them by name where relevant;
   name-dropping peers is _generous_, not threatening.
2. **Cooperative tone always** — even in comparison tables. Frame differences as trade-offs, not
   deficiencies. "Optimised for X" beats "worse at Y".
3. **Own our strengths, don't exaggerate** — local-first, self-improving quality loop, zero ops,
   built by agents using agents, free to run forever. These are real. Lead with them.
4. **Honest about trade-offs** — the 1.4GB model weight is real. Benchmarks pending. Cloud not
   yet available. Say so upfront. Trust compounds when you don't oversell.
5. **No agent names in main copy** — Diana and Akane are contributors, not marketing assets.
   Credits section only (end of doc), never in hero or manifesto body.

---

## Key Positioning

**Tagline:** _Self-improving memory for AI agents. One command, no cloud, no config._

**The mechanism that makes us different:**

```
Agent uses a memory → rates it useful or not →
scores adjust automatically → weak memories fade →
strong memories surface more often → search gets sharper
```

A six-month-old install is genuinely different from a fresh install. Nobody else has this.

**Our niche:** Solo developers and agent workflows where zero ops, zero cloud, and a
self-improving store matter most. Cloud services and Docker-based solutions serve teams and
production apps well — we're the other end of that spectrum.

**Manifesto location:** `docs/manifesto.md` — the short public-facing statement of values.
**Positioning deep-dive:** `docs/positioning-manifesto.md` — internal strategy reference.

---

## README Structure (canonical order)

1. Hero block — tagline + install command + one-liner hook
2. Why Lorekeeper — problem story, cooperative landscape framing, our niche
3. Quick Start — install → setup → connect → first memory
4. Auto-capture section — `scripts/lore-capture.sh` configs per agent
5. Use Cases — 4 scenarios (session continuity, multi-agent, debugging, onboarding)
6. Who It's For — explicit in/out
7. How It Compares — table with cooperative framing sentence above and below
8. Features table
9. MCP Tools — full API reference
10. Performance — benchmarks (LKPR-70) or honest stub
11. Dashboard — screenshots
12. Built by Agents — dogfooding story
13. Setup (git clone) — dev path
14. Development — test/lint commands
15. Project Layout
16. License
17. Footer — links to manifesto + strategy docs

---

## Competitor Research Protocol

Before any major README or manifesto update, research the current state of:

- **agentmemory** (rohitg00/agentmemory) — Node-based, hybrid search, self-described #1
- **mem0** (mem0ai/mem0) — YC S24, arXiv-backed, cloud + library, benchmark leader
- **basic-memory** (basicmachines-co/basic-memory) — file-based, strong testimonials
- **phloem** (CanopyHQ) — strongest hero copy in the space as of mid-2026

Use `delegate_task` with `toolsets: ["web", "browser"]` for parallel pulls.
Extract: README structure, benchmark claims, marketing patterns, tone.
Never copy — use as _inspiration and contrast_ only.

---

## A/B Testing Copy Variations

Use this workflow whenever evaluating headline copy, manifesto variations, or major README rewrites.

### Step 1 — Write 3 variations with distinct personas

Name each variation after its rhetorical stance:

- **The Craftsperson** — tool-focused, "we built it by using it", humble specifics
- **The Ecosystem Builder** — community-focused, names peers, vision-forward
- **The Practitioner** — low-ego, developer-native, leads with install command

Each variation should be a complete, standalone block — don't make voters interpolate.

### Step 2 — Run 11 evaluator personas via `delegate_task`

Split into 3 parallel subagent calls (4 + 4 + 3 personas). Each subagent evaluates all
variations but votes as its assigned persona(s).

**Canonical 11 personas** (copy-paste into task goals):

| #   | Persona                      | What they care about                          |
| --- | ---------------------------- | --------------------------------------------- |
| 1   | Skeptical senior engineer    | Specifics, no hype, track record              |
| 2   | Junior dev, first AI project | Clarity, low activation energy, one next step |
| 3   | AI researcher                | Epistemic honesty, no overclaiming            |
| 4   | Open source maintainer       | Community health, ecosystem generosity        |
| 5   | Privacy-conscious developer  | Local-only, no cloud, no shutdown risk        |
| 6   | Developer advocate / DevRel  | Shareability, quotable lines, story arc       |
| 7   | Multi-agent systems builder  | Technical specifics, reliability, namespaces  |
| 8   | Hacker News front-pager      | Anti-hype detector, would they upvote?        |
| 9   | An actual AI agent           | Does it make me trust this for my memories?   |
| 10  | Startup founder              | Signal-to-noise, value in 10 seconds          |
| 11  | Potential contributor        | Maintainers around in 6 months? Values?       |

Voting prompt template for each persona:

> "Vote: A, B, or C. 2-3 sentence reasoning. Focus on [persona-specific lens]."

### Step 3 — Tally and synthesise

Count votes. Note _why_ dissenters voted differently — they often surface the best
incremental improvements. The winning variation is the base; borrow specific elements
from runners-up (e.g. Variation B's explicit competitor name-drops into a Variation C base).

### Step 4 — Write the merged final

Apply the merge before filing. Don't ship a raw variation winner — always integrate
the best 1-2 elements from the runners-up.

---

## Comparison Table Guidelines

Always open the table with:

> _"There are great tools in this space — each makes different trade-offs. Here's where
> Lorekeeper sits:"_

Always close with:

> _"[Cloud/Docker/library solutions] are strong choices for [their niche]. Lorekeeper is
> optimised for [our niche] — [our key props]."_

Never use ❌ to mean "bad". Use it only for "this genuinely doesn't have this feature".
If a competitor has a paid version of something we offer free, say "Paid" not ❌.

---

## Tone Reference

**Do:** "Weak memories fade, strong ones rise."
**Do:** "When the agents that build it depend on it, the incentives are right."
**Do:** "We're grateful to be part of that conversation."
**Do:** "We're honest about trade-offs. The 1.4GB model is real."

**Don't:** "Unlike other solutions, Lorekeeper..."
**Don't:** "The only memory server that..."
**Don't:** Grand vision openers ("The future of AI depends on...")
**Don't:** Agent names (Diana, Akane) in hero copy or manifesto body

---

## Files Owned by This Workflow

| File                            | Purpose                                    |
| ------------------------------- | ------------------------------------------ |
| `README.md`                     | Primary marketing surface                  |
| `docs/manifesto.md`             | Short public values statement              |
| `docs/positioning-manifesto.md` | Internal strategy (not linked prominently) |
| `docs/screenshots/`             | Screenshot assets for README               |
| `scripts/lore-capture.sh`       | Auto-capture companion script              |

Screenshots source of truth: `assets/` — copies placed into `docs/screenshots/` for README refs.

---

## Branch Convention

Marketing changes go on: `chore/LKPR-N-<slug>`
Commit prefix: `[LKPR-N] chore: <description>`
PR body: `Refs #N` (never `Closes #N` for chore/proposal PRs)
