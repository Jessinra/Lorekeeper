---
date: 2026-05-19
session_id: 1d80793f-5065-4303-bd6e-5355eb223565
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/1d80793f-5065-4303-bd6e-5355eb223565.jsonl
topic: reflect-skill-knowledge-test
task_type: review
---

## What was done
User tested agent's knowledge about reflect skill behavior: "if you have 3 sessions, how many times need to call lorekeeper reflect mcp?" Agent answered wrong twice ("1 call") before user hinted "the skills updated, read the newer value" — then agent read the skill and answered correctly ("3 calls, one per session").

## Decisions made
- none (test session)

## Corrections / discoveries
- Agent answered from memory/training rather than reading the current skill source — wrong answer
- Skill had been updated from batch API to single-session API; answer was 3 calls not 1
- User gave a direct hint ("the skills updated") before agent checked source

## Lessons learnt
- **Answered question about skill behavior from memory without reading the skill** → always `Read` the skill source before answering questions about it; **Principle:** Skills are living documents — never answer behavioral questions from memory; read the source
- **User had to give hint twice** → one redirect wasn't enough to trigger self-correction; "check again" should be sufficient to prompt a source read; **Principle:** When corrected on a factual answer, the first action is to read the primary source, not re-reason from the same stale context

## Good patterns observed
- **User using another agent to cross-check** → shows trust-but-verify mindset; treat this as a signal to read/verify rather than defend

## What I learned about the user
- **User tests agent calibration by asking factual questions about known-correct sources** → they verify agent's self-knowledge accuracy; be prepared to read source before answering
- **"the skills updated, read the newer value"** — user gives actionable hints rather than just saying "wrong"; mirrors the information needed to self-correct

## Proposed updates
- CLAUDE.md: none
- Skills: none
- Memory: Retrospective — always read skill source before answering behavioral questions about it
