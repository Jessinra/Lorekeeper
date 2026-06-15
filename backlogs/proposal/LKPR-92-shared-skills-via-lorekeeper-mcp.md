---
id: LKPR-92
title: Cross-profile skill sharing via Lorekeeper-owned canonical directory
type: feature
sprint: ~
rice_score: ~
github_issue: 211
filed_by: Akane
filed_date: 2026-06-15
---

# [LKPR-92] Cross-profile skill sharing via Lorekeeper-owned canonical directory

## Problem

Skills created by one agent (e.g., Akane under the `akane` profile) are not visible to other agents (Diana, Bella, Chisa). Each profile has its own `~/.hermes/profiles/<name>/skills/` directory with no automatic propagation. When Diana needs a workflow Akane already built, she either rebuilds it from scratch or someone manually copies the SKILL.md over.

Skills are structured procedural code (YAML frontmatter, step-by-step instructions) with a distinct lifecycle from Lorekeeper's declarative knowledge — they need frequent patching, file-level operations, and name-based reference from cron jobs. So the solution shouldn't pull them into Lorekeeper's vector DB. But the **discovery and storage** can be unified.

## Solution

Establish a canonical shared skills directory owned by Lorekeeper, making skills automatically available to all agents without per-profile propagation.

**Architecture:**

1. Lorekeeper repo gets a `shared-skills/` directory at its default data root (next to whatever Lorekeeper considers its home).
2. Each Hermes profile's session bootloader reads from both `shared-skills/` (canonical) and `profiles/<name>/skills/` (private overrides, same name wins).
3. Skill CRUD (create, update, delete) goes through Lorekeeper's MCP server — e.g. `mcp_lorekeeper_skill_create`, `mcp_lorekeeper_skill_patch` etc. — which reads/writes to `shared-skills/`.
4. Loading at session start remains filesystem-fast. No MCP call per skill — just an additional directory in the load path.
5. `skill_manage` defaults to shared; a `--scope private` flag writes to the local profile instead.

**What this does NOT do:**

- Skills stay as structured markdown files on disk — not in the vector DB
- Lorekeeper's MCP server just handles file I/O + name validation
- No changes to skill loading semantics, cron job skill references, or skill content format

## Acceptance Criteria

- [ ] `shared-skills/` directory exists under Lorekeeper's data root (or configurable path)
- [ ] MCP tool(s) added for reading/writing skill files in `shared-skills/`
- [ ] Hermes bootloader reads `shared-skills/` before profile-local skills/ for each profile
- [ ] `skill_manage create` writes to `shared-skills/` by default
- [ ] `skill_manage create --scope private` writes to the active profile's skills/
- [ ] Existing per-profile skills continue to work unchanged (private wins when names collide)
- [ ] Cron jobs that reference shared skill names resolve correctly without config changes
- [ ] CI passes, existing skills tests unaffected

## Affected Files

**Backend:**

- Lorekeeper repo: `shared-skills/` directory + new MCP handler module for skill CRUD
- Hermes session bootloader: add `LORE_SHARED_SKILLS_DIR` to the skill load path
- `skill_manage` tool: add `--scope private` option, default to shared

**Dashboard (if applicable):**

- `_none_` — backend-only change

## Dependencies

- _None_ — standalone feature. Build order: Lorekeeper side first (directory + MCP tools), then Hermes bootloader changes.

## Required Updates

- **CLAUDE.md**: [ ] Describe shared-skills/ directory and the new MCP tools
- **README.md**: [ ] N/A
- **Skills**: [ ] No existing skills change. The proposal-filing skill and other skills already guide skill operations — may need minor updates to reflect the new shared default
- **Backlog**: [ ] N/A

## Decisions

1. **Configurable path** — yes, use `LORE_SHARED_SKILLS_DIR` env var, default to `<LORE_DATA_DIR>/shared-skills/`
2. **Delete semantics** — remove the skill file from disk, but keep a tombstone record in a DB table so agents don't re-create it. The tombstone prevents the name from being reused (or warns on reuse).
3. **Indexing in query** — shared skills are indexed in Lorekeeper's search (discoverable by query), but stored as skill references with different metadata from memories. Not mixed into the memory vector store as memories.

## Notes

Filed after conversation with Jason. See session 2026-06-15 (Telegram DM). Initial thinking was to integrate skills into Lorekeeper's vector DB, but rejected because skills are structured code with a different lifecycle (frequent edits, file ops, cron name references). The shared-directory approach gives cross-profile propagation without that architectural mismatch.
