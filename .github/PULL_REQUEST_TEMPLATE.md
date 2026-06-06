## Summary

<!-- What does this PR do? Link the ticket: Closes #LKPR-XX -->

## Changes

-

## Checklist

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
