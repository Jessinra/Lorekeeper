---
date: 2026-05-21
session_id: 85c8af31-f3fb-4058-8825-58ac45754656
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-prompt/85c8af31-f3fb-4058-8825-58ac45754656.jsonl
topic: vip-plus-opc-braindump
task_type: design
---

## What was done

Jason shared a braindump of a new VIP+ project PRD and asked for organized notes scoped to OPC/Digital Checkout. Produced structured notes in `vip-plus-opc-notes.md`. Key corrections applied based on Jason's domain knowledge of the project.

## Decisions made

- Refund part in original notes was wrong — current PRD is from the old version, so refund constraints were initially marked ❌ instead of ✅ (corrected)
- Food OPC is not in checkout scope (skip entirely)
- One-time payment IS allowed in the new VIP+ design

## Corrections / discoveries

- **Refund flow correction**: Initial notes said refunds weren't allowed for VIP+ → Jason corrected that refund IS a new addition in this version (the PRD was from the old version)
- **Netflix upcharge**: N orders, 1 payment transaction — QR/one-time payment prompts only once regardless of child order count
- **Orders and payments are decoupled**: N orders can share 1 payment transaction in VIP+ design

## Lessons learnt

- **Always check which PRD version you're reading** — an old PRD can have the opposite constraints of the current version
- **Ask for clarification on refund/charge flow** — this is often the most counterintuitive part of subscription billing

## Good patterns observed

- **Braindump organization**: Take unstructured notes and scope them to the relevant subsystem (OPC/Digital Checkout), then validate assumptions
- **Correction integration**: When Jason corrected the refund logic, the fix was applied immediately and the rationale documented

## What I learned about the user

- Jason has deep knowledge of the VIP+ domain and catches wrong assumptions about billing/refund flows quickly
- VIP+ upgrade charges full price + separate refund of unused balance (not pro-rated delta)
- Food OPC exclusion is a known design boundary for checkout scope

## Proposed updates

- Memory: VIP+ upgrade flow charges full price + separate refund of unused VIP balance (not pro-rated delta)
- Memory: VIP+ order/payment decoupling — N orders can share 1 payment transaction
