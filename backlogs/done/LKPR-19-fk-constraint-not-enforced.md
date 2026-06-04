---
id: LKPR-19
title: FK constraint not enforced in link_store — test_fk_rejects_missing_memory failing
type: bug
sprint: unplanned
rice_score: ~
filed_by: Akane
filed_date: 2026-05-22
resolved_date: 2026-05-22
---

# [LKPR-19] FK constraint not enforced in link_store

## Problem

`tests/test_link_store.py::test_fk_rejects_missing_memory` fails with:

```
Failed: DID NOT RAISE <class 'sqlite3.IntegrityError'>
```

The test expects SQLite to reject a link referencing a non-existent memory (FK violation), but no error is raised.

## Solution

Ensure every SQLite connection in `link_store.py` runs `PRAGMA foreign_keys = ON` after opening. SQLite FK enforcement is off by default — `PRAGMA foreign_keys = ON` must be set on every new connection.

Additionally, re-raise `sqlite3.IntegrityError` in `insert_link` so the test expectation is satisfied.

## Acceptance Criteria

- [x] `PRAGMA foreign_keys = ON` is set on every connection after opening
- [x] `test_fk_rejects_missing_memory` passes — missing memory link raises `sqlite3.IntegrityError`
- [x] Existing behavior for valid links is unchanged

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention

## Completed

Date: 2026-05-22
Branch: fix/LKPR-19-fk-constraints-link-store
Commit: pragma FK fix + re-raise IntegrityError in insert_link
Reviewed by: Akane — solid work ✓

## Notes

- Pre-existing before LKPR-16/LKPR-3 — not introduced by recent changes
- Low risk, small fix
