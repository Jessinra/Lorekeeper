---
date: 2026-05-20
session_id: 83a945ff-2580-4537-9eb7-90f4e458a32d
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-digital-checkout/83a945ff-2580-4537-9eb7-90f4e458a32d.jsonl
topic: svip-oneclick-parent-child-order
task_type: design
---

## What was done

Designed the parent-child order model for VIP+ (SVIP one-click purchase). Confirmed the 1-order-1-plan_id constraint in the current schema, then designed additive DB columns (parent_order_id, digital_item_type) to support bundling. Chose Option B for maximum backward compatibility.

## Decisions made

- **Parent-child order model** — Since current schema enforces 1 Order = 1 plan_id (digital_order_tab, OrderInfo struct), bundling requires parent-child decomposition.
- **Option B (additive columns)** — Add parent_order_id + digital_item_type to existing tables. Most backward compatible. No table restructuring.
- **DC generates child order IDs** — The checkout system creates child order identifiers rather than relying on upstream services.
- **Simultaneous payment → shared spm_transaction_id** — When all items paid together, children share the parent's transaction ID.
- **Deferred payment → separate transaction_id** — If items are paid individually, each gets its own transaction.

## Corrections / discoveries

- The current schema's 1-order-1-plan_id constraint is structural, not accidental — the OrderInfo struct and digital_order_tab are both designed around a single plan per order.
- Parent-child with additive columns means zero migration risk for existing orders (they simply have NULL parent_order_id).

## Lessons learnt

- **Additive columns beat table restructuring every time** — NULL defaults on new columns means old records require no migration; **Principle:** prefer additive schema evolution over structural changes for critical production databases.
- **Transaction ID sharing is a payment concern, not an order concern** — The order model stays clean; payment grouping is handled at the spm_transaction_id level. **Principle:** separate order semantics from payment semantics.

## Good patterns observed

- **Option B evaluation framework** — Multiple design options considered, each judged against backward compatibility, implementation complexity, and migration risk. **Principle:** always produce at least 2-3 options and evaluate against the same criteria.
- **DC owns child ID generation** — Keeping ID generation within the checkout system avoids cross-service coupling for a purely internal concern. **Principle:** generate local identifiers locally; delegate only when the ID must be cross-system.

## What I learned about the user

- Systematically evaluates multiple design options before committing
- Particularly focused on backward compatibility — it's the primary criterion that shapes decisions
- Distinguishes cleanly between order semantics and payment semantics, even when they interact
- Prefers the checkout system to own its own identifiers rather than delegating

## Proposed updates

- CLAUDE.md: none
- Skills: none
- Memory: none
