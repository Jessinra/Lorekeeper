<!--
  PR CONVENTIONS
  ==============

  Branch prefix   | Purpose              | Body convention
  ----------------|----------------------|-----------------------------------------------
  proposal/       | Proposal tickets     | Use "Refs #N" — DO NOT use "Closes #N"
  feat/, fix/,    | Implementation work  | Use "Closes #N" — auto-closes on merge
  chore/, etc.    |                      |

  The CI checks this. If "proposal/" branch + "Closes #" → fail.
-->

## Summary

<!-- For proposal PRs: Refs #LKPR-N -->
<!-- For feature/fix PRs: Closes #LKPR-N -->

## Changes

-

## Standard Checklist

### General

- [ ] Tests added or updated for new behaviour
- [ ] `uv run pytest` passes locally
- [ ] `uv run ruff check src tests scripts/` passes locally
- [ ] `uv run mypy src` passes locally

### Adding or changing an MCP tool (`@mcp.tool`)

> Skip this section if no MCP tools were added, renamed, or removed.

- [ ] `README.md` — tool documented under `### \`lore\_<name>\`` with example payload and return shape
- [ ] `README.md` — tool count in the intro line updated (e.g. "Exposes N MCP tools")
- [ ] `README.md` — tool name listed in the intro tool list
- [ ] `server.py` comment / module docstring updated if it lists tool names
- [ ] `assets/prompts/lorekeeper-agent-prompt.md` updated if agents need to know about the new tool
- [ ] `scripts/check_mcp_docs.py` — verify it passes (`uv run python scripts/check_mcp_docs.py`)

### Removing or renaming an MCP tool

- [ ] All checklist items above
- [ ] Old tool name removed from README and prompt files
- [ ] Existing skills that reference the old tool name updated

### High-risk changes (scoring, dedup, soft-delete, migrations)

> Skip if this PR doesn't touch memory ranking, duplicate detection, scoring, or persistence.

- [ ] Regression test added that would catch a scoring regression
- [ ] Migration is additive and idempotent (safe to run more than once)
- [ ] Existing migration entries NOT modified — new entry added with strictly higher version number
- [ ] `CLAUDE.md` architecture section updated if the change affects the hybrid scoring formula

---

## Merge Contract

A PR is mergeable when:

- ✅ All `blocker:` comments resolved
- ✅ All `issue:` (MAJOR) comments resolved OR follow-up ticket created with reason to defer
- ✅ CI gates green: lint → type check → tests → PR size
- ✅ At least 1 human approval
