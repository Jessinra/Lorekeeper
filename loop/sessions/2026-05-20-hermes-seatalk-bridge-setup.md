---
date: 2026-05-20
session_id: 20260520_104827_53c24d93
transcript: /Users/jessin.donnyson/.hermes/sessions/20260520_104827_53c24d93.jsonl
topic: hermes-seatalk-bridge-setup
task_type: build
---

## What was done

Jason set up the Hermes agent initially (who are you, accessing code directory). Then reconfigured the reply routing: messages from SeaTalk should reply back to SeaTalk (not Telegram) by default. The bridge LaunchAgent was already set up but had missing env vars. Claude fixed the plist to include all env vars (`SEATALK_SIGNING_SECRET`, `HERMES_SECRET`, `HERMES_WEBHOOK_URL`), reloaded it, and verified the bridge is up at PID 62295 with `KeepAlive=true`. A test via SeaTalk confirmed the flow: SeaTalk → Hermes → skynet-base → SeaTalk reply.

## Decisions made

- SeaTalk → Hermes → SeaTalk is the default flow (not Telegram)
- Telegram only if explicitly requested in the message
- `{__raw__}` template used so Hermes sees full payload
- Bridge plist uses `KeepAlive=true` + `RunAtLoad=true` for persistence

## Corrections / discoveries

- The plist was loaded but only passed `HOME` env var — `SEATALK_SIGNING_SECRET` etc. were missing
- `code: 3001` error when replying to non-subscriber employee codes — identified as a permissions error on SeaTalk API
- LaunchAgent path: `~/Library/LaunchAgents/io.seatalk.hermes.bridge.plist`
- Bridge logs: `~/Library/Logs/seatalk-hermes-bridge.log`

## Lessons learnt

- **LaunchAgent plist needs all env vars explicitly listed** → `RunAtLoad=true` runs before shell profile, so env vars aren't inherited; **Principle:** always verify env vars in plist config, not just `HOME`
- **SeaTalk reply error 3001** → can only reply to bot subscribers, not arbitrary employee codes

## Good patterns observed

- **Health check after restart** → `curl /health → {"status": "ok"}` before declaring success; **Principle:** always verify with health check after infrastructure changes

## What I learned about the user

- **Jason expects background services to be permanent** → "it should run permanent with cmdctl" — he expects `KeepAlive=true` LaunchAgent management, not manual starts
- **Jason tests immediately** → he sent a real SeaTalk test after the fix to verify
