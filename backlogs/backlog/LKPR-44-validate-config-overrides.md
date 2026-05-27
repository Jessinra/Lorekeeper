---
id: LKPR-44
title: Validate config overrides before applying on restart
type: bug
status: S:ready
priority: P2:medium
sprint: 2
rice_score: ~  # TBD: R:5 I:6 C:95% E:0.1w
filed_by: Diana
filed_date: 2026-05-27
---

# [LKPR-44] Validate config overrides before applying on restart

## Problem

`server.py:init_service()` loads persisted config overrides from the `config_overrides` table and applies them via:

```python
setattr(s, key, value)
```

This bypasses Pydantic's type validation and coercion. If someone corrupts the `config_overrides` table — e.g., sets `decay_lambda` to a string, or `auto_link_k` to zero — the MCP server silently fails to initialize on the next restart. The only symptom: the server doesn't respond to tools. No error message in the UI, no way to recover except wiping the table manually.

The config overrides table is written by the dashboard Config tab, which passes strings from form inputs. The client-side Pydantic model (`ConfigUpdate`) validates types, but nothing stops a stale corrupted value from a prior session or a direct DB edit from breaking startup.

## Solution

Replace the bare `setattr` with a try/except block that logs the failure and skips the bad override:

```python
for key, value in overrides.items():
    try:
        setattr(s, key, value)
        getattr(s, key)  # at least confirm it reads back
    except (ValueError, TypeError, AttributeError) as e:
        log.warning("config_override_skipped", key=key, value=value, error=str(e))
```

Minimum viable: catch + log + skip. The server starts, the dashboard shows the override as missing, and the operator can re-apply it correctly.

## Acceptance Criteria

- [ ] If `config_overrides` table has a value that doesn't match the field type, the server starts successfully
- [ ] The bad override is logged with a clear warning
- [ ] The bad override is skipped (not applied)
- [ ] All 87 existing tests pass unchanged

## Affected Files

- `src/lorekeeper/server.py` — replace bare `setattr` with validated apply loop

## Dependencies

None

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Should we delete the bad override from the table so it doesn't block *every* future restart? Yes — but that's a nice-to-have. Minimum is skip + log.

## Notes

~20-line change, no new dependencies, no test changes needed. High confidence fix. This is specifically about the startup path. The dashboard write path is already guarded by `ConfigUpdate` Pydantic model.