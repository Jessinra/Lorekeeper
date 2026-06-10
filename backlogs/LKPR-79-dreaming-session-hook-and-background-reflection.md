---
id: LKPR-79
title: Dreaming — session hook + background reflection engine
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-10
github_issue: 179
---

# [LKPR-79] Dreaming — session hook + background reflection engine

## Problem

Lorekeeper's reflection/link-recommendation system (the "dreaming" workflow) currently depends on a Hermes cron job that calls `lore_reflect` via agent tools. This has two problems:

1. **Non-Hermes users have no reflection** — Claude Code, Cursor, and other MCP clients don't have `session_search` or cron infrastructure. They can use Lorekeeper's memory tools but get none of the consolidation benefits.
2. **Even for Hermes users, cron-to-MCP auth is fragile** — CLI cron jobs don't inherit agent configs, MCP credentials, or API keys reliably (Claude Code in cron can't access its API key). Users hit this wall and bounce.

Competitors have solved this: Anthropic's Claude Dreaming is a server-side async API endpoint; OpenAI's ChatGPT Dreaming V3 runs as a background process during idle compute; OpenClaw uses cron + CLI scripts (same auth problem Lorekeeper has).

MCP protocol cannot force an agent to run a task — its notifications are one-way status updates only. `sampling/createMessage` is the closest mechanism but requires client opt-in and human-in-the-loop review. There is no reliable way to push work to an agent via MCP.

## Solution

Add dreaming capabilities directly into Lorekeeper as a long-lived server process, removing the dependency on external cron or agent cooperation. Two-phased approach:

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

- Stores the session in a new `sessions` table (existing or extended) marked as `unprocessed`
- Immediate return (fire-and-forget from agent's perspective)
- No blocking on reflection — the hook is just capture
- Tool name aligns with "hook" pattern agents understand

### Phase 2: Reflect — background thread in Lorekeeper server

A background thread/task inside the Lorekeeper server process that:

- Runs on a configurable schedule (default: daily, via `config.yaml`)
- Reads unprocessed sessions from the store
- Calls the same internal logic as `lore_reflect` + `lore_recommend_links`
- Uses the server's own DB credentials — no external auth needed
- Sleeps/deactivates when idle (no CPU cost between runs)

Since Lorekeeper is already a persistent MCP server (launchd/systemd/sidecar), the user already keeps it running. The background thread piggybacks on that uptime.

### Phase 3 (future): Cloud-hosted dreaming

For Lorekeeper Cloud, a dedicated background worker processes unprocessed sessions with its own LLM. No user infrastructure required — the cloud service handles the full dreaming loop.

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

Filed after research across MCP spec, Claude Dreaming API docs, ChatGPT Dreaming V3, and OpenClaw Dreaming. MCP has no viable server→client push mechanism for task execution (sampling requires client opt-in + human-in-the-loop; notifications are one-way status only). Server-side background thread is the only reliable approach for self-hosted users.

Lorekeeper is already a long-lived server process — adding a background thread is a small incremental cost vs. the user experience improvement of zero-setup dreaming.
