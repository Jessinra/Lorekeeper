---
date: 2026-05-21
session_id: 20260521_201444_7cd093c3
source: telegram
topic: opc-core-build-test
task_type: build
---

## What was done

Jason switched to opc-core working dir via Telegram. Ran make clean, make build. Build hit a dependency resolution issue on `git.garena.com/shopee/mts/go-application-server/control-center/sdk` (exit code 2). Jason said "i see it building ok" (possibly misreading the error), then asked to run make test and fix all failing cases.

Key constraint: "do not change actual code, only change test code"

Gateway was restarted during the session, interrupting the agent. Model was switched mid-session from deepseek/deepseek-v4-flash to claude-sonnet-4.6.

## Decisions made

- Only test code may be modified in this session — production code is off-limits
- Gateway restart handled gracefully (session history was intact on resume)

## Observations

- Jason may skim build output and miss non-zero exit codes
- OPC-core build pipeline had a dependency resolution problem (possibly temporary or VPN-related)
- Telegram-driven sessions for opc-core are for testing/fixing only, not feature work
