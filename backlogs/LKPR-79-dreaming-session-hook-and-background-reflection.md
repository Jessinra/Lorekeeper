---
id: LKPR-79
title: Dreaming — session hook + background reflection engine
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-10
github_issue: 179
github_pr: 180
---

# [LKPR-79] Dreaming — session hook + background reflection engine

## Problem

Lorekeeper's reflection/link-recommendation system (the "dreaming" workflow) currently depends on a Hermes cron job that calls `lore_reflect` via agent tools. This has two problems:

1. **Non-Hermes users have no reflection** — Claude Code, Cursor, and other MCP clients don't have `session_search` or cron infrastructure. They can use Lorekeeper's memory tools but get none of the consolidation benefits.
2. **Even for Hermes users, cron-to-MCP auth is fragile** — CLI cron jobs don't inherit agent configs, MCP credentials, or API keys reliably (Claude Code in cron can't access its API key). Users hit this wall and bounce.

Competitors have solved this: Anthropic's Claude Dreaming is a server-side async API endpoint; OpenAI's ChatGPT Dreaming V3 runs as a background process during idle compute; OpenClaw uses cron + CLI scripts (same auth problem Lorekeeper has).

MCP protocol cannot force an agent to run a task — its notifications are one-way status updates only. `sampling/createMessage` is the closest mechanism but requires client opt-in and human-in-the-loop review. There is no reliable way to push work to an agent via MCP.

## Solution

Core architecture: **capture locally, dream in the cloud, sync results back**. The local Lorekeeper server collects session data; the dreaming engine runs wherever it can get an LLM — cloud service for hosted users, or a local background thread for self-hosted.

### Phase 1: Capture — `lore_session_hook` tool

A new MCP tool that agents call at the end of a session to submit raw conversation data for reflection:

```
lore_session_hook(
    session_id="...",
    summary="What was accomplished",
    messages=[
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ]
)
```

- Stores the session in the local store, marked as `unprocessed`
- Immediate return (fire-and-forget from agent's perspective)
- No blocking on reflection — the hook is just capture
- Works with any MCP client, not just Hermes

### Phase 2: Dream — cloud service (primary path)

When Lorekeeper Cloud exists, a dedicated cloud worker:

- Pulls unprocessed sessions from the local store (via API sync)
- Runs the dreaming pipeline (reflection + link discovery + memory consolidation)
- Uses the cloud's own LLM — no local compute needed
- Writes results (new memories, links, reflections) back to the local store

The user's local Lorekeeper stays lean — just capture and respond. All the LLM work happens server-side.

### Phase 3 (fallback): Dream — local background thread (self-hosted)

For users who don't use Lorekeeper Cloud, a background thread inside the Lorekeeper server process handles dreaming:

- Runs on a configurable schedule (default: daily, via `config.yaml`)
- Reads unprocessed sessions from local store
- Calls the same reflection + link discovery logic
- Uses its own LLM config (separate from search embeddings — different model/prompt)
- Sleeps when idle

Lorekeeper is already a persistent server (launchd/systemd/sidecar) — the thread piggybacks on that uptime. No cron, no agent cooperation needed.

## Acceptance Criteria

- [ ] `lore_session_hook` tool exists and accepts session_id + summary + messages
- [ ] Hook stores sessions as `unprocessed` in the store
- [ ] Background thread runs on configurable interval (config.yaml, default daily)
- [ ] Thread reads unprocessed sessions, runs reflection + link discovery internally
- [ ] No external cron, no agent cooperation, no CLI needed for the reflect step
- [ ] Existing `lore_reflect` and `lore_recommend_links` MCP tools remain for manual/interactive use
- [ ] All Hermes agents migrate from cron-based reflection to the server-side approach

## Affected Files

**Backend:**

- `src/lorekeeper/handlers.py` — add `lore_session_hook` tool registration
- `src/lorekeeper/services/reflection_store.py` — extend ReflectionStore with unprocessed session queue
- `src/lorekeeper/dreaming/` — new module: background schedulers, reflection engine, config
- `src/lorekeeper/config.py` — add dreaming config section (interval, enabled/disabled)

**Dashboard (if applicable):**

- `_none_` — reflection is backend-only; dashboard can show status later

## Dependencies

_None_ — independent of current sprint work

## Required Updates

- **CLAUDE.md**: [ ] Add dreaming module path and config docs
- **README.md**: [ ] Add dreaming setup/usage section
- **Skills**: [ ] Update `reflect` skill to use `lore_session_hook` instead of Hermes-specific session discovery. Remove cron-based reflection once server-side is stable.
- **Backlog**: [ ] After Phase 1, mark existing reflection cron tickets as superseded

## Open Questions

- Should the background thread use Lorekeeper's own LLM config for reflection, or should it be independently configured (model, prompt)? Independent config seems safer — different use case from search embedding.
- Should unprocessed sessions have a TTL? If agent calls hook but reflection never runs, sessions accumulate.
- Should the background thread expose a `lore_dream_status` tool so the agent can check when last reflection ran?

## Notes

Filed after research across MCP spec, Claude Dreaming API docs, ChatGPT Dreaming V3, and OpenClaw Dreaming. MCP has no viable server→client push mechanism for task execution (sampling requires client opt-in + human-in-the-loop; notifications are one-way status only).

**Architecture decision:** "capture locally, dream in the cloud, sync results back." The local server never needs an LLM for dreaming — it just stores session data. The dreaming engine (reflection + link discovery) runs wherever it has LLM access: cloud service for hosted users, local thread as self-hosted fallback. This keeps the local Lorekeeper install lean and avoids forcing users to configure an LLM just for dreaming.
