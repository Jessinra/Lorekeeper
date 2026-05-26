---
date: 2026-05-20
session_id: 83a945ff-2580-4537-9eb7-90f4e458a32d
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-digital-checkout/83a945ff-2580-4537-9eb7-90f4e458a32d.jsonl
topic: vip-plus-order-model-design
task_type: design
---

## What was done

Jason asked Claude to assess the VIP+ order model — specifically whether to use ext_info blob, a new grouping table, or additive DB columns for the parent-child order relationship. Claude analyzed the existing `digital_order_tab` schema and confirmed: 1 order = 1 plan_id, no order-item entity. Jason chose Option B (additive columns). The final design decisions were documented into Section 13 of the VIP+ notes doc and saved to Lorekeeper.

## Decisions made

- **Parent-child order model via new DB columns** (additive, backward-compatible):
  - `parent_order_id BIGINT UNSIGNED NOT NULL DEFAULT 0`
  - `digital_item_type TINYINT`
- Ext_info blob rejected: not queryable, messy
- Group table rejected: over-engineering for v1
- Simultaneous payment → shared `spm_transaction_id`; deferred payment → separate transactions
- DC returns child order IDs in `CreateOrderResponseData`
- Child order IDs: DC generates for new/upgrade, User BE generates for renewals

## Corrections / discoveries

- `digital_order_tab` has no order-item entity — each row is 1 digital subscription plan
- The "abstract digital item" pattern means orders are flat, not hierarchical in current schema
- `CreateOrderResponseData` currently only returns `NavigationAction` — needs new field for child order IDs

## Lessons learnt

- **Additive DB columns beat ext_info blob for structured relationships** → queryable, typed, backward-compatible; **Principle:** prefer schema-level constraints over JSON blobs for relationships
- **Always check current response struct before proposing new fields** → `CreateOrderResponseData` gap found via code read

## Good patterns observed

- **Lorekeeper save during design session** → the decision rationale is persisted immediately, not just in chat log; **Principle:** save design decisions to Lorekeeper during the session
- **Section-by-section doc update** → added Section 13 with structured agreed design; **Principle:** keep the design doc as the single source of truth

## What I learned about the user

- **Jason decides and documents** → he picks from options, then wants the decision captured in the doc immediately
- **Jason thinks in constraints** → "backward compatible" and "no datafix" are key decision criteria
