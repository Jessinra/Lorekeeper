---
id: LKPR-19
title: FK constraint not enforced in link_store — test_fk_rejects_missing_memory failing
type: bug
status: backlog
priority: low
filed_by: Akane
filed_date: 2026-05-22
---

# [LKPR-19] FK constraint not enforced in link_store

## Symptom
`tests/test_link_store.py::test_fk_rejects_missing_memory` fails with:
```
Failed: DID NOT RAISE <class 'sqlite3.IntegrityError'>
```

The test expects SQLite to reject a link referencing a non-existent memory (FK violation), but no error is raised.

## Likely Cause
SQLite FK enforcement is off by default. `PRAGMA foreign_keys = ON` needs to be set on every connection after opening.

## Fix
In `link_store.py`, ensure every connection runs `PRAGMA foreign_keys = ON` after opening.

## Notes
- Pre-existing before LKPR-16/LKPR-3 — not introduced by recent changes
- Low risk, small fix
