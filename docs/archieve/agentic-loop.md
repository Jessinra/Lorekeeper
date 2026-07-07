# Continuous Learning Agent System — Brainstorm

**Date**: 2026-05-13
**Topic**: Designing an automated learning system for a local Claude agent

---

## Goal

Build a reinforcement-learning-inspired system where the agent:

- Memorizes each chat session (key points, decisions, corrections)
- Periodically consolidates learnings
- Auto-updates `CLAUDE.md`, skills, MCP configs
- Becomes a coherent, continuously improving agent over time

---

## The Core Loop

```
Session Start → Load Context → Work → Extract Learnings → Consolidate → Update Agent Config → Repeat
```

Claude Code already has most of the primitives — hooks, memory, skills, CLAUDE.md, cron. What's missing is the **orchestration glue** that ties them into a closed loop.

---

## Components Needed

### 1. Session Lifecycle Hooks (the "sensors")

Claude Code hooks (`settings.json`) can trigger scripts on events:

- **Pre-session hook**: Loads relevant memories, primes context, injects "reflection prompt"
- **Post-session hook**: Captures the session transcript, triggers the learning pipeline

Challenge: hooks today run shell commands, not full Claude conversations. Need a lightweight script that queues work for a background agent.

### 2. Episodic Memory Store (the "hippocampus")

Beyond the current memory system (good for facts), need **episodic memory** — structured session summaries:

```
session/
  2026-05-13-checkout-debugging.md    # what happened, what worked
  2026-05-13-td-review.md             # decisions made, patterns seen
  ...
```

Each episode captures:

- **Task type** (debugging, code gen, review, brainstorm)
- **Key decisions** and their outcomes
- **Tools/skills used** and effectiveness
- **User corrections** (strongest learning signal)
- **Patterns observed** in the codebase

### 3. Knowledge Consolidation Engine (the "sleep cycle")

Periodically reviews episodic memories and distills into durable knowledge:

- **Merge similar episodes** into generalized rules
- **Detect repeated patterns** → create new skills
- **Update CLAUDE.md** with proven conventions
- **Prune stale knowledge** that contradicts recent experience

Could run as a **cron-scheduled Claude agent** that:

1. Reads recent episodes
2. Compares against existing CLAUDE.md / skills / memories
3. Proposes updates (or auto-applies with guardrails)

### 4. Reinforcement Signal Extraction

The "reward function" for the learning loop. Signals ranked by strength:

| Signal                                         | Strength        | How to Capture                               |
| ---------------------------------------------- | --------------- | -------------------------------------------- |
| Explicit user correction ("no, don't do that") | Strongest       | Parse transcript for correction patterns     |
| User acceptance without edits                  | Strong positive | Task completed, no follow-up corrections     |
| Repeated tool failures                         | Negative        | Count retries per tool/approach              |
| Session length vs. task complexity             | Weak            | Short session = efficient; long = struggling |
| User re-asking same question across sessions   | Strong negative | Cross-session dedup detection                |

### 5. Self-Modifying Agent Config

What the system can actually update:

| Target                               | What Changes                      | Risk Level |
| ------------------------------------ | --------------------------------- | ---------- |
| `CLAUDE.md`                          | Coding conventions, project rules | Low        |
| `memory/` files                      | Facts, preferences, references    | Low        |
| Skills (`.claude/skills/`)           | New workflows, refined prompts    | Medium     |
| `settings.json` (hooks, permissions) | Behavioral triggers               | High       |
| MCP server configs                   | New tool integrations             | High       |

Higher-risk changes should require human approval. Lower-risk ones can auto-apply.

---

## Architecture Options

### Option A: "Journal + Reconcile" (simplest, recommended start)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Each Session│────▶│  Journal Entry│────▶│  Periodic Recon  │
│  (normal use)│     │  (auto-saved) │     │  (cron agent)    │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │ Updates:         │
                                          │ • CLAUDE.md      │
                                          │ • memories/      │
                                          │ • skills/        │
                                          └─────────────────┘
```

- **How**: Post-session hook runs a script that appends a structured summary to a journal file. A scheduled agent (daily/weekly) reads the journal and reconciles.
- **Pros**: Low complexity, uses existing primitives, safe
- **Cons**: Batch learning (not real-time), journal can grow large

### Option B: "Event-Driven Pipeline" (more sophisticated)

```
┌─────────┐    ┌───────────┐    ┌────────────┐    ┌──────────┐
│ Session  │───▶│ Transcript│───▶│ Extraction │───▶│ Knowledge│
│ Hook     │    │ Parser    │    │ Agent      │    │ Graph    │
└─────────┘    └───────────┘    └────────────┘    └─────┬────┘
                                                        │
                                              ┌─────────▼─────────┐
                                              │ Diff Generator     │
                                              │ (what changed in   │
                                              │  knowledge graph)  │
                                              └─────────┬─────────┘
                                                        │
                                              ┌─────────▼─────────┐
                                              │ Config Updater     │
                                              │ CLAUDE.md / skills │
                                              └───────────────────┘
```

- **How**: Custom MCP server or local service that processes transcripts in real-time, maintains a knowledge graph (could be as simple as SQLite + embeddings), and generates config diffs.
- **Pros**: Real-time learning, structured knowledge, queryable
- **Cons**: More infrastructure, needs embedding model locally

### Option C: "Meta-Agent" (most ambitious)

A **dedicated Claude agent** that monitors other sessions and acts as a "learning supervisor":

- Watches session logs via a cron loop
- Has its own CLAUDE.md that defines learning objectives
- Can spawn sub-agents to test hypotheses ("does this new skill work better?")
- Maintains a changelog of all self-modifications
- Has rollback capability if changes degrade performance

This is essentially **meta-learning** — an agent that learns how to make another agent learn better.

---

## Practical Implementation Plan

### Phase 1 — Capture (week 1)

- Create a post-session hook that auto-summarizes each conversation into `log/sessions/`
- Structure: task type, tools used, corrections received, outcome
- Use the `lorekeeper-memorize` skill as the storage backend

### Phase 2 — Reconcile (week 2)

- Build a `reconcile` skill that reads recent session logs
- Compares against current CLAUDE.md and memories
- Generates a diff of proposed updates
- Presents for approval (human-in-the-loop)

### Phase 3 — Automate (week 3)

- Schedule the reconciliation as a cron agent (daily)
- Auto-apply low-risk changes (memory updates)
- Queue high-risk changes (CLAUDE.md, skills) for review
- Add a "learning dashboard" skill that shows what's been learned

### Phase 4 — Close the loop (week 4+)

- Add pre-session context injection based on task type detection
- Track improvement metrics (session length, correction frequency)
- Experiment with skill auto-generation from repeated patterns

---

## Key Design Principles

1. **Human-in-the-loop for high-risk changes** — never auto-modify skills or CLAUDE.md without review until you trust the system
2. **Append-only journal, reconciled periodically** — don't try to learn in real-time at first; batch processing is more robust
3. **Explicit > implicit signals** — user corrections are gold; inferred signals are noisy
4. **Rollback everything** — git-track all config changes so you can revert bad learning
5. **Separate observation from action** — the system that extracts learnings should not be the same one that applies them

---

## Open Questions

1. **Scope**: Just one project, or across all projects globally?
2. **Trust level**: Auto-apply memory updates, or require approval for everything?
3. **Biggest pain point**: Agent forgets context? Makes same mistakes? Doesn't know preferences?
