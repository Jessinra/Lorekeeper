---
id: LKPR-102
title: lorekeeper status CLI command
type: feature
status: S:proposal
priority: P2:medium
sprint: ~
rice_score: ~ # TBD — needs a concrete trigger
filed_by: Akane
filed_date: 2026-06-20
github_issue: 238
---

# [LKPR-102] `lorekeeper status` CLI command

## Problem

After running `lorekeeper setup`, new users have no quick "did it work?" confirmation step. The only way to see any memory stats is to open the web dashboard (requires server running). There's no shareable summary of Lorekeeper's state — no output to paste into a HN comment, Reddit post, or GitHub issue to show "my agent remembers 157 things and is getting better."

Existing users also lack a quick CLI way to check the feedback loop is working: "is my memory quality improving over time?"

## Solution

Add a `lorekeeper status` subcommand that queries the MetricsStore and MemoryStore for aggregates and prints a formatted summary to stdout.

**Flow:**

1. User runs `lorekeeper status`
2. CLI queries `MemoryStore.all_memory_rows()` for total count, average score, top 5 by score, top 5 by usage
3. CLI queries `MetricsStore` for total API calls, per-tool breakdown
4. CLI computes score delta (avg score now vs N days ago) for quality trend
5. CLI queries reflection store for session count
6. Outputs formatted markdown to stdout

**Output shape (default):**

```
## Lorekeeper Status v0.3.0
**Data:** ~/.lorekeeper

**Memories:** 157 total | avg score: 7.2 | +12% this week
**Sessions:** 12 | **Usage:** 1,284 MCP calls
**Quality trend:** ↑ improving (score delta +0.4 over 7 days)

**Top memories by score:**
1. Project onboarding checklist (9.2)
2. Team member preferences (8.8)
3. Sprint review notes (8.5)
4. Architecture decisions (8.3)
5. Client meeting summary (8.1)

**Top tools used:** lore_search (43%), lore_remember (28%), lore_insert (15%), lore_update (10%),
lore_forget (4%)
```

**Options:**

- `--json` — machine-readable JSON output
- `--days N` — trend window (default 7)

**Extends:** CLI, not MCP tools — no new MCP surface area. New `status` subparser in `__main__.py` that delegates to a `cli/status.py` module.

## Acceptance Criteria

- [ ] `lorekeeper status` prints formatted summary to stdout without errors
- [ ] Output includes: total memory count, average score, score delta over N days, session count, total usage count, top 5 memories by score, top 5 by usage
- [ ] `lorekeeper status --json` outputs valid JSON with all fields
- [ ] `lorekeeper status --days 14` accepts custom trend window (defaults to 7)
- [ ] Works without the web dashboard running — standalone CLI tool
- [ ] Zero MCP surface area added (no new tools, no new handlers)
- [ ] Logs go to stderr (stdout is reserved for formatted output)
- [ ] `lorekeeper status` on a fresh DB (zero memories) prints graceful empty state: "No memories yet. Run `lorekeeper setup` to get started, or use your agent to start remembering."

## Affected Files

**Backend:**

- `src/lorekeeper/__main__.py` — add `status` subparser
- `src/lorekeeper/cli/status.py` — new module: aggregate queries + formatting
- `src/lorekeeper/services/memory_store.py` — may need an aggregate query method (count, avg_score, top by score, top by usage)
- `src/lorekeeper/services/metrics_store.py` — may need a total usage aggregate
- `tests/cli/test_status.py` — new test file for the status command

**Dashboard (if applicable):**

_none_ — CLI-only

## Dependencies

_none_ — independently shippable

## Required Updates

- **CLAUDE.md**: [ ] N/A — no architectural change
- **README.md**: [ ] Add `lorekeeper status` to CLI usage section, add sample output to the "Quick Start" or "Usage" section
- **Skills**: [ ] N/A — no agent-facing MCP changes
- **Backlog**: [ ] N/A

## Open Questions

- Should the empty state suggest next actions beyond `lorekeeper setup`? (e.g., "Try asking your agent to remember something")
- Should `lorekeeper status` auto-start the metrics/score computation if the service isn't running? (Proposal: yes — standalone SQLite reads don't need the MCP server)

## Notes

- Filed from daily-ideas cron run 2026-06-20. Jason approved filing.
- Phase A alignment: narrative creation (shareable summary for HN/Reddit/GitHub), feedback loop visibility (score trend), onboarding confirmation/post-setup dopamine hit
- Risk register link: platform absorption (2412737f) — a shareable status output is portable, works offline, can be posted anywhere. Low-cost distribution asset independent of any platform.
- Simplicity check: pure SQL aggregates (COUNT, AVG, ORDER BY + LIMIT) — no LLM calls, no complex computation
