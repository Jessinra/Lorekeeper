# LKPR-58: Session End Hook for Automatic Capture

**Status:** Plan  
**Ticket:** [LKPR-58 / LKPR-12](https://github.com/Jessinra/Lorekeeper/issues/58)  
**Date:** 2026-06-04

---

## Goal

Make session-end reflection automatic (or nearly so) by wiring a `loop/hooks/post_session.sh` hook that can be triggered when a session ends. The agent already has all the tools (`lore_insert`, `lore_reflect`, the `lorekeeper-protocol` skill) — the missing piece is the trigger mechanism and a tested, documented end-to-end path.

---

## Current State

- `loop/` directory does **not exist** in the repo
- `lorekeeper-protocol` skill already encodes a solid Phase 3 workflow (insert → reflect)
- `lore_reflect` and `lore_insert` MCP tools are fully functional
- No `lore_extract_session` MCP tool exists — and per the ticket, it's **not needed** if the protocol skill covers it (it does)

---

## Proposed Approach

**No new MCP tool.** The ticket explicitly allows skipping `lore_extract_session` if the protocol skill covers the pattern. It does. Adding a tool just to return a JSON scaffold is net-negative complexity.

Instead:

1. **Create `loop/hooks/post_session.sh`** — a shell script that accepts a session transcript (stdin or file arg) and invokes Hermes with the `lorekeeper-protocol` skill to process it
2. **Document the hook** in CLAUDE.md (hook contract, how to wire it)
3. **Write an integration test** that verifies: transcript in → memories inserted + reflection recorded

---

## Step-by-Step Plan

### Step 1 — Create `loop/` directory structure

```
loop/
└── hooks/
    ├── post_session.sh      ← main deliverable
    └── README.md            ← hook contract docs
```

### Step 2 — Implement `loop/hooks/post_session.sh`

**Contract:**
- Input: session transcript via `$1` (file path) or stdin
- Env required: `LORE_NAMESPACE`, `HERMES_PROFILE` (optional, defaults to calling profile)
- Behaviour: invokes Hermes CLI with the `lorekeeper-protocol` skill and the transcript as context, instructing it to run Phase 3 (insert + reflect)
- Exit codes: 0 = success, 1 = transcript missing/empty, 2 = Hermes invocation failed

**Sketch:**
```bash
#!/usr/bin/env bash
set -euo pipefail

TRANSCRIPT="${1:-}"
if [[ -z "$TRANSCRIPT" ]]; then
    # try stdin
    TRANSCRIPT=$(cat)
fi
if [[ -z "$TRANSCRIPT" ]]; then
    echo "[post_session] ERROR: no transcript provided" >&2
    exit 1
fi

PROFILE="${HERMES_PROFILE:-diana}"

hermes run \
    --profile "$PROFILE" \
    --skill lorekeeper-protocol \
    --message "$(printf 'SESSION TRANSCRIPT:\n%s\n\nRun Phase 3 of the lorekeeper-protocol: insert new memories and call lore_reflect for this session.' "$TRANSCRIPT")"
```

> **Note**: exact `hermes run` invocation needs validation against current Hermes CLI — may need `hermes chat --non-interactive` or a different flag. Spike this before committing.

### Step 3 — Write `loop/hooks/README.md`

Document:
- What the hook does
- How to wire it (Hermes session end → call this script)
- The env vars it reads
- Expected output / side effects (memories created, reflection recorded)
- How dedup handles repeated calls (existing dedup prevents double-inserts)

### Step 4 — Integration test

**File:** `tests/test_lkpr58_post_session_hook.py`

Test approach — **avoid spawning a real Hermes process**. Instead test the underlying plumbing:

1. Provide a mock session transcript
2. Verify the hook correctly passes it to the Hermes invocation (subprocess mock)
3. Separately, write an end-to-end functional test using `MemoryService` directly:
   - Simulate what the lorekeeper-protocol would do after reading a transcript
   - Call `svc.insert(...)` + `svc.submit_reflection(...)` in sequence
   - Assert memories are stored, reflection is recorded, `session_id` shows up in `get_processed_session_ids()`

**Test cases:**
- `test_hook_requires_transcript` — exits 1 when no transcript given
- `test_hook_invokes_hermes` — subprocess mock verifies correct args
- `test_reflect_after_insert_stores_correctly` — functional, no subprocess
- `test_idempotent_reflect` — calling with same session_id twice returns `already_processed=True`

### Step 5 — Update CLAUDE.md

Add to the "Living Agentic Loop" section:
- Hook location: `loop/hooks/post_session.sh`
- How to trigger it
- Dedup guarantee: existing dedup + `already_processed` guard mean it's safe to call multiple times

---

## Files to Change

| File | Action |
|---|---|
| `loop/hooks/post_session.sh` | **CREATE** — main deliverable |
| `loop/hooks/README.md` | **CREATE** — hook contract |
| `tests/test_lkpr58_post_session_hook.py` | **CREATE** — integration tests |
| `CLAUDE.md` | **UPDATE** — document hook location |

**No changes to:** `server.py`, `services/`, `models.py` — no new MCP tool needed.

---

## Risks / Open Questions

1. **`hermes run` CLI shape** — need to spike the exact invocation before finalising the script. Check `hermes --help` or the `hermes-agent` skill.
2. **Transcript format** — what does a Hermes session transcript actually look like when dumped? Is it JSON, plain text, markdown? The script needs to handle the real format.
3. **Profile isolation** — `LORE_NAMESPACE` must be set correctly so memories land in the right namespace. The script should inherit from the caller's env or require explicit passing.
4. **Hermes CLI availability** — the hook assumes `hermes` is on PATH. Should fail fast and clearly if not.

---

## AC Checklist

- [ ] `loop/hooks/post_session.sh` implemented and triggerable
- [ ] Protocol skill covers extraction (✅ already done — existing `lorekeeper-protocol` skill)
- [ ] Duplicate risk handled (✅ existing dedup + `already_processed` guard)
- [ ] E2E test: transcript in → memories inserted + reflect recorded
