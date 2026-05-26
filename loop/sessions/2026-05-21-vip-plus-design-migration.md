---
date: 2026-05-21
session_id: 258bb5db-3340-4ffb-b209-5020894930d9
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-digital-checkout/258bb5db-3340-4ffb-b209-5020894930d9.jsonl
topic: vip-plus-design-migration
task_type: design
---

## What was done

Designed the parent-child order model and migration strategy for VIP+ subscription + one-time purchase support. Finalized OrderItem proto schema, prepurchase display approach (Solution C), and renewal flow compatibility. Documented phased migration with hard gate conditions.

## Decisions made

- **OrderItem as generic item model** — Contains plan_id, price, ext_info (proto-serialized bytes). Can represent a subscription plan OR arbitrary item (e.g. Netflix upgrade). From DC perspective everything is just items.
- **Parent-child order model confirmed** — New DB columns (parent_order_id, digital_item_type) rather than changing the 1-order-1-plan_id constraint. Option B (additive columns) chosen for maximum backward compatibility.
- **Solution C for prepurchase display** — Two parallel get_page calls with a page_type field. No breaking changes to existing API surface.
- **Renewal flow gets same treatment** — CreateOrderRenewalRequest also uses the parent-child model.
- **User BE provides two APIs** — get_refund_info and subscribe_and_terminate for lifecycle management.
- **Quick upgrade banner via display_mode flag** — Simple toggle for display without structural changes.
- **Phased rollout with hard gates** — Migration is "very very critical and important" and must be properly documented at every phase.

## Corrections / discoveries

- OrderItem is inherently abstract — it doesn't need to know what it represents, just carry the data. The ext_info bytes allow arbitrary domain-specific payloads without tight coupling.
- A single deployment can handle both old (single-plan) and new (parent-child) order models simultaneously via the digital_item_type column.

## Lessons learnt

- **Migration complexity grows with deferred decisions** → Document every phase before coding begins; **Principle:** phased rollouts need phase-level documentation, not just a migration doc.
- **"Very very critical" features need explicit rollback plan** → The user emphasized this repeatedly; **Principle:** migration design must include undo strategy at every gate.

## Good patterns observed

- **Solution C (parallel calls, no breaking changes)** — By adding a page_type field and keeping old endpoints intact, zero existing clients break. **Principle:** design for coexistence, not replacement.
- **Abstract item model** — OrderItem doesn't model subscription vs one-time at the proto level; it just carries bytes. This keeps the DC layer decoupled from domain specifics. **Principle:** keep transport schemas generic, push domain logic to the consumer.

## What I learned about the user

- Prioritizes backward compatibility above all else — every design option was evaluated on "does this break existing code?"
- Thinks in phased rollouts with explicit gates; doesn't ship big-bang migrations
- Has a strong sense of what's "very very critical" and expects commensurate documentation rigor
- Prefers additive schema changes over structural refactors (Option B over Option A)

## Proposed updates

- CLAUDE.md: none
- Skills: none
- Memory: none
