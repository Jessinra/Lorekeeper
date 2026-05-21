---
date: 2026-05-21
session_id: 45309420-239a-49c6-a9c6-3532c666f73d
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-prompt/45309420-239a-49c6-a9c6-3532c666f73d.jsonl
topic: opc-write-td-skill-update
task_type: build
---

## What was done

Jason asked to study his TD writing style from 4 real Confluence docs (1 HLS + 3 TDs), then update the `opc-write-td` skill to match. Spawned parallel subagents to study each doc. Extracted full style analysis (structure, language, tone, API table conventions, diffs, cross-referencing). Updated `td-sections.md` with pattern-matched per-section guidance. Created `writing-style.md` reference file documenting subtle style patterns. Updated `SKILL.md` to Phase 2 split Biz Goal vs Tech Goal, and added reference to new style guide. Committed as a3971ed.

## Decisions made

- All Data Mart checkboxes start unchecked by default — the SVIP TD was an example, not a template
- "Document review & signoff" is a standard section Jason includes in the TD skeleton
- Safety/downgrade mechanisms documented as a callout block after the implementation table
- `writing-style.md` is a separate reference file (not merged into td-sections.md) to keep per-section guidance clean

## Corrections / discoveries

- Data Mart checkboxes were pre-checked from the SVIP TD example — Jason corrected: "all Data Mart checkboxes should start unchecked by default"
- Jason explicitly asked to verify the skill is in install-skills whitelist and committed after the update

## Lessons learnt

- **Jason's style is distinctive**: OPC-perspective ("OPC needs to...", "OPC will pass..."), → for causality chains, parenthetical hedges like (ideally), (best effort), (TBC) throughout
- **Strikethrough for confirmed non-issues**: Items that are confirmed as not a problem get ~~strikethrough~~ formatting
- **Version controls are meticulous**: Color-coding, tracked reasons, explicit ACK columns

## Good patterns observed

- **Parallel subagent study**: 3 subagents studied 4 docs concurrently, extracted full raw content — much faster than sequential fetching
- **Style analysis before writing**: Extracting the patterns first, then updating the skill, avoids guessing at conventions

## What I learned about the user

- Jason tracks skill hygiene actively — after updating a skill he always asks to verify whitelist + commit
- Jason writes from OPC's perspective (not a neutral observer) — "OPC needs to...", "OPC will pass..."
- Uses parenthetical hedges extensively — (ideally), (TBC), (best effort), (new)
- Prefers → for causality chains over prose explanations

## Proposed updates

- Memory: Insert Jason's TD writing style patterns for future opc-write-td usage
- Memory: Data Mart checkboxes default to unchecked
