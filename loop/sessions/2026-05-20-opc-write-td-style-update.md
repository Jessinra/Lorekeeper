---
date: 2026-05-20
session_id: 45309420-239a-49c6-a9c6-3532c666f73d
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-prompt/45309420-239a-49c6-a9c6-3532c666f73d.jsonl
topic: opc-write-td-style-update
task_type: build
---

## What was done

Jason pasted 4 Confluence TD URLs for Claude to study and update the `opc-write-td` skill with a writing style guide derived from actual TDs. Claude fetched all docs in parallel, analyzed patterns, updated `td-sections.md`, created `writing-style.md`, and updated `SKILL.md`. Jason then asked for a full cohesion review. Claude found and fixed: wrong pre-checked Data Mart checkboxes, missing Document review section, wrong Appendix naming, and a SVIP-specific bias in the price section. Committed as `a3971ed`.

## Decisions made

- Writing style extracted from 4 real TDs (SVIP, VN subscription, BN subscription, checkout flow)
- Data Mart checkboxes should all start unchecked — pre-checked implies always correct
- "Document review & signoff" section is required (from VN and BN TDs)
- Safety/downgrade mechanisms documented as a callout after the implementation table
- Price/Financial section generalized to remove SVIP-specific bias

## Corrections / discoveries

- Writing style: use "OPC needs to..." not "the system needs to..." — always from OPC's perspective
- Heavy use of `→` for causality, parenthetical hedges `(ideally)`, `(TBC)`, `(best effort)` are Jason's idiom
- Toggle Compatibility Matrix goes in Appendix, not inline

## Lessons learnt

- **Study real TDs before writing style guides** → abstract style guides drift from actual practice; ground them in 3+ real examples; **Principle:** style guides must derive from real artifacts, not invented conventions
- **Cohesion review after writing** → find scope leakage, wrong defaults, and SVIP bias; **Principle:** always review skill content for bias toward the most recent use case

## Good patterns observed

- **Parallel Confluence fetching** → all 4 docs in parallel; **Principle:** parallelize reads
- **`writing-style.md` as a separate reference file** → keeps SKILL.md lean; **Principle:** separate workflow instructions from style/reference content

## What I learned about the user

- **Jason writes from OPC's perspective** → "OPC will pass", "OPC needs to" — not "the system"
- **Jason uses `→` for causality heavily** — signature pattern in his TDs
- **Jason's TDs use hedge words** — `(ideally)`, `(TBC)`, `(best effort)` are standard hedges
