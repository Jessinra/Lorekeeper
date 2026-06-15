---
id: LKPR-89
title: lore_setup MCP tool — agent-guided linear onboarding flow
type: feature
sprint: ~
github_issue: 205
rice_score: ~
filed_by: Akane
filed_date: 2026-06-12
---

# [LKPR-89] lore_setup MCP tool — agent-guided linear onboarding flow

## Problem

Installing Lorekeeper is "fast" (uvx, one command) but the gap between install and a working MCP memory server is larger than it looks:

1. User installs Lorekeeper
2. User needs to configure their agent to connect to the MCP server
3. User needs to seed initial memories
4. User needs to verify search works
5. User needs to understand the feedback loop
6. User has to read docs, piece together steps, and troubleshoot alone

Currently this gap is bridged by LKPR-55 (seed prompt) and LKPR-7 (static setup docs). Neither is a guided flow. The user either reads docs and configures manually, or the agent configures itself through trial and error.

The core insight: **MCP servers can direct agent behavior through structured dialog.** A setup MCP tool is an onboarding wizard where the server teaches the agent how to set itself up, step by step.

## Solution

A single MCP tool `lore_setup` that runs a linear (non-branching, non-LLM) state machine:

**Input:** `{ state: string, result: string }`

- `state` — the state token from the previous response, or `"start"` for initial call
- `result` — the agent's output from executing the previous step's instructions

**Output:** `{ state: string, prompt: string, status: string }`

- `state` — next step token or `"complete"` when done
- `prompt` — instructions for the agent to execute
- `status` — `"in_progress"` or `"complete"` or `"error"`

### Setup Steps (7 steps, linear, no branching)

| #   | Step          | Agent does                                                            | Server validates                                          |
| --- | ------------- | --------------------------------------------------------------------- | --------------------------------------------------------- |
| 1   | **doctor**    | Run `uvx lorekeeper doctor` and return output                         | Output contains success indicators for Chroma/SQLite/port |
| 2   | **config**    | Add MCP entry to their agent's config file per server's template      | Agent reports "added to config" (≥10 chars)               |
| 3   | **seed**      | Read project key files and `lore_remember` 5+ facts about the project | At least 5 non-deleted memories exist in DB               |
| 4   | **search**    | Call `lore_search(query="<one of the seeded facts>")`                 | Search returns ≥1 result matching seeded content          |
| 5   | **feedback**  | Call `lore_update(id=<a memory>, useful=True, confidence=8)`          | Score of that memory changed from previous value          |
| 6   | **dashboard** | Fetch `<http://localhost:7777/health>` or verify the dashboard loads  | Dashboard responds 200                                    |
| 7   | **complete**  | Show summary and mark onboarding done                                 | Persist `lore_setup_complete: true` in ConfigStore        |

### Validator approach (no LLM)

Each step's validator is a pure function:

- **doctor:** regex match for success patterns in output string
- **config:** non-empty result, agent claims success
- **seed:** count memories via `MemoryStore.count_active()` — must be ≥5
- **search:** exec a `lore_search` via `MemoryService.search()`, check result count
- **feedback:** compare memory score before/after a synthetic `lore_update` call
- **dashboard:** HTTP GET to `http://localhost:7777/`
- **complete:** all previous steps passed, set ConfigStore override

No LLM calls, no conditional branches. If a step's validator fails, the same `prompt` is returned (retry with additional context from `result`). After 3 failures on the same step, return `status: "error"` with a troubleshooting link.

### Completion persistence

When step 7 passes, store `lore_setup_complete: true` in ConfigStore (survives server restart). On subsequent calls with `state: "start"`, return `status: "complete"` with a prompt offering to re-onboard (clearing the flag first).

### Entry point

A copy-paste prompt for the README:

> "You have a new MCP tool called `lore_setup`. Call `lore_setup(state='start')` and follow each prompt until setup is complete."

The user pastes this to their agent. The agent discovers the tool, calls it, and the dialog runs. No auto-detect, no hooks, no injection — the user explicitly initiates.

## Acceptance Criteria

- [ ] `lore_setup(state="start")` returns step 1 prompt
- [ ] 7 linear steps complete sequentially with no branching
- [ ] Each step validator is a pure function with no LLM dependency
- [ ] After step 7, `lore_setup_complete` is persisted in ConfigStore
- [ ] Subsequent calls with `state="start"` return `status: "complete"` and offer re-onboarding
- [ ] After 3 failures on one step, return `status: "error"` with docs link
- [ ] Copy-paste prompt documented in README and quickstart
- [ ] Full setup run takes <2 minutes from paste to completion
- [ ] Works with Claude Code, Cursor, Copilot, Hermes, Codex (any agent with MCP tool support)

## Non-goals

- No auto-detection or agent injection (user-initiated only)
- No branching on agent type (same linear flow for all agents)
- No LLM-generated troubleshooting (docs link for hard failures)
- No partial progress persistence (start over if interrupted)
- No MCP transport negotiation (use the already-connected transport)

## Affected Files

**New:**

- `src/lorekeeper/tools/setup.py` — `lore_setup` tool handler with state machine, validators, and step definitions
- `tests/test_setup_tool.py` — unit tests for each step validator and state machine

**Modified:**

- `src/lorekeeper/handlers.py` or equivalent tool registry — register `lore_setup` as a new MCP tool
- `pyproject.toml` — update `[project.scripts]` if `lore_setup` has CLI dependencies
- `README.md` — add copy-paste setup prompt under "Quick start"
- `docs/quickstart.md` — replace current static setup section with the copy-paste prompt approach

## Dependencies

- LKPR-55 (seed prompt): the seed step can reuse the prompt template from LKPR-55 or generate its own based on project content

## Required Updates

- **CLAUDE.md**: [ ] add `lore_setup` tool to the MCP tools list
- **README.md**: [ ] replace current setup section with copy-paste prompt
- **Skills**: [ ] `lorekeeper-memorize` — note that `lore_setup` seed step auto-populates initial memories, no separate seeding workflow needed
- **Backlog**: [ ] When shipped, LKPR-55 (seed prompt) becomes partially superseded — its content feeds into step 3 but the dedicated prompt file may no longer be needed standalone

## Open Questions

- Should step 2 (config) accept agent-type parameter to emit the right config format? (Claude Code JSON vs. Cursor rules vs. Hermes config.yaml vs. Codex CLI config) — arguably yes but adds branching. Alternative: emit a generic MCP config template and let the agent adapt it.
- Should `content` field be validated against seeded facts in step 4, or just check count? Full content validation would need semantic similarity comparison — scope creep for v1.
- What happens if the user runs setup on an already-configured instance with 200 memories? Step 3 (≥5 memories) passes instantly, step 1 (doctor) still runs for health check. The flow degrades gracefully.
- Error recovery: if step 2 fails, the agent presumably can't continue. Should the server suggest manual steps or just point to docs?

## Notes

Filed per Jason's direction after the MCP "setup tool" concept was discussed. The core idea: MCP servers can direct agent behavior through structured dialog, teaching the agent how to configure itself step by step. This turns a static README into a living onboarding experience.

The state machine is intentionally linear and LLM-free. The server validates each step with pure functions (regex, DB counts, HTTP checks). The agent executes, reports, and receives the next instruction. No AI needed on the server side — just a deterministic state machine.
