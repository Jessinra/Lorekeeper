---
id: LKPR-72
title: Beta release QA — install flow, quickstart walkthrough, dashboard UX audit
type: chore
sprint: unplanned
rice_score: ~
filed_by: Jason
filed_date: 2026-06-08
github_issue: 165
---

# [LKPR-72] Beta release QA — install flow, quickstart walkthrough, dashboard UX audit

## Problem

Beta ships when `pip install lorekeeper-mcp` + running lorekeeper gives a working dashboard and MCP
round-trip in <2 minutes, with no bugs that break core functionality. Several blockers existed:

- `lorekeeper --help` launched the MCP stdio server instead of printing help
- FastMCP printed an update-nag banner (`🎉 Update available: 3.4.2`) on every startup
- `pyproject.toml` version is `0.2.0` and matches the package metadata used in this branch
- Two pytest deprecation warnings: `asyncio_mode` unknown config, `StarletteDeprecationWarning`
- `docs/quickstart.md` did not exist
- README wheel filename referenced old version `2.0.0`

## Solution

Three gates define done:

- **Gate 1** — Install flow: clean `lorekeeper --help`, no nag banner, version aligned, tests clean
- **Gate 2** — Quickstart: `docs/quickstart.md` exists, literal follow-through in ≤2 min (warm cache)
- **Gate 3** — Dashboard: all 7 tabs load, no P1 bugs

## Acceptance Criteria

- [x] `lorekeeper --help` prints usage/description and exits cleanly (does NOT start the server)
- [x] `lorekeeper --version` prints the version and exits cleanly
- [x] No FastMCP update-nag banner on startup — clean structlog JSON only
- [x] `uv run pytest -q` runs with 0 warnings (except third-party FutureWarning from mem0)
- [x] `pyproject.toml` version remains `0.2.0` and the CLI/docs match that package version
- [x] `docs/quickstart.md` exists and passes prettier lint
- [x] Quickstart covers: prerequisites, clone + setup.sh, restart agent, start dashboard, seed memories, verify MCP round-trip
- [x] All 7 dashboard tabs load without blank screens or JS console errors
- [x] README updated: wheel filename corrected, `--help`/`--version` mentioned, quickstart link added

## Affected Files

**Backend:**

- `src/lorekeeper/__main__.py` — add argparse wrapper before MCP startup
- `pyproject.toml` — bump fastmcp to >=3.4.2, keep version at 0.2.0, add pytest-asyncio to dependency-groups, add filterwarnings

**Docs:**

- `docs/quickstart.md` — new file
- `README.md` — wheel filename, --help mention, quickstart link

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [x] Updated — wheel filename, --help flags, quickstart link
- **Skills**: [ ] lorekeeper-dev pitfalls updated
- **Backlog**: [x] This ticket → move to done on merge

## Gate 1 Findings

| Check                  | Result                                                                                             |
| ---------------------- | -------------------------------------------------------------------------------------------------- |
| `lorekeeper --help`    | ✅ Prints usage, exits — fixed via argparse wrapper in `__main__.py`                               |
| `lorekeeper --version` | ✅ Prints `lorekeeper 0.2.0`, exits                                                                |
| FastMCP nag banner     | ✅ Gone — upgraded fastmcp to 3.4.2                                                                |
| pytest warnings        | ✅ Zero project warnings — added pytest-asyncio to dependency-groups, filterwarnings for starlette |
| Version                | ✅ `0.2.0` in pyproject.toml                                                                       |

## Gate 2 Findings

- `docs/quickstart.md` created, 152 lines
- Honest timing: ~2 min warm cache, ~5 min cold (sentence-transformers ~90 MB)
- Passes prettier lint

## Gate 3 Findings — Dashboard Audit

All 7 tabs audited with real data (459 memories, 37 links, 197 sessions):

| Tab      | Result                                                                        |
| -------- | ----------------------------------------------------------------------------- |
| Memories | ✅ Table, stats bar, score colouring, namespace badge all render              |
| Detail   | ✅ All fields: title, description, content, score, confidence, usage, dates   |
| Links    | ✅ 37/37 links, source/relation/target/reason/score/uses all render           |
| Query    | ✅ Search returns results with combined/semantic/keyword breakdown            |
| Sessions | ✅ 197 sessions, task-type filter sidebar, date/topic/task/summary all render |
| Config   | ✅ All LORE\_\* config fields editable                                        |
| Backup   | ✅ Export button, import file chooser, soft-deleted toggle                    |
| Metrics  | ✅ Heatmaps render, per-tool breakdown visible                                |

**P1 bugs found:** 0
**P3 issues:** 0

## Open Questions

_None_

## Notes

Branch: `lkpr-72-beta-release-qa`
Commits: 5 commits total (2420eea → 3e88049)
Tests: 266/266 passing throughout
