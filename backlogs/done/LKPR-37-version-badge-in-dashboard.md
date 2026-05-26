---
id: LKPR-37
title: Show git version badge in dashboard header
type: feature
status: S:done
priority: P3:low
sprint: unplanned
rice_score: ~
filed_by: Jason
filed_date: 2026-05-25
---

# [LKPR-37] Show git version badge in dashboard header

## Problem

After pulling latest code, there's no way to tell if the dashboard has reloaded with the new version. Need to see the git commit/tag at a glance.

## Solution

Add a `/api/version` endpoint that runs `git describe --always --dirty --tags` and display the result as a monospace badge in the dashboard header, next to the memories/links meta line. If the endpoint fails (no git repo), show `unknown`.

## Acceptance Criteria

- [ ] Header shows version badge: `v0.1.0` (or short commit hash, with `-dirty` if uncommitted changes)
- [ ] After `git pull` + reload, the badge updates to the new version
- [ ] Graceful fallback to `unknown` if git is unavailable

## Affected Files

**Backend:**

- `src/lorekeeper/dashboard/app.py` — add `_get_version()` + `/api/version` GET endpoint

**Dashboard:**

- `static/index.html` — add `<span class="version-badge">` element in header
- `static/css/styles.css` — monospace badge styling
- `static/js/app.js` — fetch version on init and populate badge

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [x] N/A
- **README.md**: [x] N/A
- **Skills**: [x] N/A
- **Backlog**: [x] N/A

## Open Questions

_None_

## Notes

Filed by Jason in Telegram, Dev implemented directly and opened PR.
