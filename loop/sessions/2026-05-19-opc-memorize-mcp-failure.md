---
date: 2026-05-19
session_id: d5bfdcfc-8466-4900-8b1b-dabed7a81ee1
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/d5bfdcfc-8466-4900-8b1b-dabed7a81ee1.jsonl
topic: opc-memorize-mcp-failure
task_type: debug
---

## What was done
User asked Claude to memorize OPC repository references (checkout core, digital-checkout, opc-core repo paths and scopes). Agent called `lore_insert` and got success responses, but data was not actually persisted. Investigation revealed the Python v2 server was returning fake success — `~/.claude/.claude.json` was still pointing to the old Node.js v1 MCP. User changed the pointer and asked Claude to migrate memories from v1 to v2.

## Decisions made
- Root cause: `~/.claude/.claude.json` was the authoritative MCP config, not `~/.claude/settings.json`
- The Python v2 server was running but not being used by the Claude Code client

## Corrections / discoveries
- **`.claude.json` is authoritative over `settings.json` for MCP config** — two separate config files, Claude Code reads `.claude.json` first
- **Python v2 server returned success without persisting** — the lore_insert handler wasn't erroring, but data didn't reach SQLite; likely a split-brain or the server was running a stale install
- 149 memories in v1 SQLite confirmed after investigation
- `lore_search` was returning results (from v1!) while `lore_insert` was silently discarding (to unconfigured v2) — mixed signals misled the agent

## Lessons learnt
- **Called `lore_insert` and reported success without verifying persistence** → should verify inserts by calling `lore_search` with the same content; **Principle:** for memory inserts, always verify with a follow-up search; success from the API does not guarantee persistence

## Good patterns observed
- **Correctly diagnosed the split-brain scenario** (search working from v1, insert failing to v2) → traced the inconsistency to its source

## What I learned about the user
- **User noticed discrepancy ("which lorekeeper are you using")** → they pay close attention to whether memory is actually working
- **User immediately diagnosed the root cause** (wrong config file) after the agent's investigation stalled → they often have deeper system knowledge; listen when they redirect

## Proposed updates
- CLAUDE.md: none  
- Skills: Update lorekeeper-memorize to include: verify with lore_search after lore_insert
- Memory: Insert: OPC Core repo references (GitLab URL, local path, scope). Insert: .claude.json is authoritative MCP config on this machine.
