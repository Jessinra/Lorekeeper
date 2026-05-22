     1|---
     2|id: LKPR-19
     3|title: FK constraint not enforced in link_store — test_fk_rejects_missing_memory failing
     4|type: bug
     5|status: backlog
     6|priority: low
     7|filed_by: Akane
     8|filed_date: 2026-05-22
     9|---
    10|
    11|# [LKPR-19] FK constraint not enforced in link_store
    12|
    13|## Symptom
    14|`tests/test_link_store.py::test_fk_rejects_missing_memory` fails with:
    15|```
    16|Failed: DID NOT RAISE <class 'sqlite3.IntegrityError'>
    17|```
    18|
    19|The test expects SQLite to reject a link referencing a non-existent memory (FK violation), but no error is raised.
    20|
    21|## Likely Cause
    22|SQLite FK enforcement is off by default. `PRAGMA foreign_keys = ON` needs to be set on every connection after opening.
    23|
    24|## Fix
    25|In `link_store.py`, ensure every connection runs `PRAGMA foreign_keys = ON` after opening.
    26|
    27|## Notes
    28|- Pre-existing before LKPR-16/LKPR-3 — not introduced by recent changes
    29|- Low risk, small fix
    30|

## Completed
Date: 2026-05-22
Branch: fix/LKPR-19-fk-constraints-link-store
Commit: pragma FK fix + re-raise IntegrityError in insert_link
Reviewed by: Akane — solid work ✓
