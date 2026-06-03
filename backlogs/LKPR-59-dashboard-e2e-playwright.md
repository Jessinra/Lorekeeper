---
id: LKPR-59
title: E2E test suite for dashboard UI (Playwright)
type: chore
status: S:ready
priority: P2:medium
sprint: ~
rice_score: ~
filed_by: Diana
filed_date: 2026-06-03
---

# [LKPR-59] E2E test suite for dashboard UI (Playwright)

## Problem

The dashboard has no browser-level automated tests. `test_dashboard.py` covers HTTP API routes via FastAPI TestClient, but nothing verifies that the JS renders correctly, user interactions work end-to-end, or that API responses are wired up to the DOM properly. Bugs at the JS↔API seam are invisible until manual testing.

This becomes urgent before a planned UI revamp — tests written now act as a behavioral safety net during redesign.

## Solution

Playwright E2E suite that spins up a real FastAPI server against a seeded temp SQLite DB and runs a real browser through the core user flows. Tests are anchored on `data-testid` attributes (not CSS selectors), so they survive HTML restructuring during the revamp.

**Scope — only stable, behavioral flows:**
- Data loading (memories tab renders rows from seeded data)
- Search (filter input narrows results)
- Delete (row disappears, confirmed via API)
- Tab switching (correct pane becomes active)
- Config toggle (saves to API, toast appears)

**Out of scope for this ticket:**
- Visual regression / screenshot comparison — add after revamp is settled
- JS unit tests (`api.js`, `state.js`) — separate ticket if needed

## Acceptance Criteria

- [ ] `pytest tests/e2e/` runs without requiring manual server startup — pytest fixture handles `uvicorn` lifecycle on a random port with isolated temp `LORE_DATA_DIR`
- [ ] Memories tab: seeded memories appear as rows on load
- [ ] Search: typing in the search box filters the displayed rows
- [ ] Delete: clicking delete on a row removes it from the DOM and the DB
- [ ] Tab switching: clicking each tab shows the correct panel, hides others
- [ ] `data-testid` attributes added to all elements the tests select (memories table, row, search input, delete button, tab buttons, toast)
- [ ] Tests pass headless (chromium)
- [ ] E2E suite gated behind `@pytest.mark.e2e` — isolated from the main `uv run pytest` unit run

## Affected Files

**Backend:**
- `tests/e2e/conftest.py` — uvicorn server fixture + temp data dir + seeded memories
- `tests/e2e/test_dashboard_e2e.py` — Playwright test cases

**Dashboard:**
- `src/lorekeeper/dashboard/templates/index.html` — add `data-testid` attributes
- JS render functions (if rows are built dynamically) — add `data-testid` in rendered HTML

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [ ] Add note on running E2E tests (`pytest -m e2e`) vs unit tests
- **README.md**: [ ] Add E2E section under Testing
- **Skills**: [ ] `lorekeeper-dev` — add E2E run instructions
- **Backlog**: [ ] N/A

## Open Questions

- Are memory rows rendered by Jinja template or JS? If JS, `data-testid`s go in the render functions, not the HTML template.
- Should E2E run on every PR or only on `main`? Playwright is ~30s — could gate to `main` only to keep PR CI fast.

## Notes

Context: discussed 2026-06-03. Decision to go E2E-first over unit/component tests — bugs live at the JS↔API seam, not inside individual JS modules. `data-testid` strategy chosen to survive the planned UI revamp — tests anchor on behavior, not structure.

Backend API coverage already exists in `tests/test_dashboard.py` (FastAPI TestClient). This ticket covers the browser rendering layer only.
