---
date: 2026-05-20
topic: seatalk-webhook-noise
task_type: build
---

## What was done

These are grouped stub entries for ~38 Hermes sessions that contain SeaTalk webhook noise — raw SeaTalk event payloads received during bridge development and testing. No substantive agent work occurred in any of them.

## Sessions in this group

| Session ID | Date/Time |
|---|---|
| 20260520_144004_e70ee285 | 2026-05-20 14:40 |
| 20260520_144037_cf3cb0b4 | 2026-05-20 14:40 |
| 20260520_144129_e6b8df7b | 2026-05-20 14:41 |
| 20260520_145354_dba67fee | 2026-05-20 14:53 |
| 20260520_145603_a273c7ba | 2026-05-20 14:56 |
| 20260520_145719_f32a30cd | 2026-05-20 14:57 |
| 20260520_145736_6d1a2894 | 2026-05-20 14:57 |
| 20260520_145808_d3ec2fea | 2026-05-20 14:58 |
| 20260520_150424_95ba04f2 | 2026-05-20 15:04 |
| 20260520_175829_082f078b | 2026-05-20 17:58 |
| 20260520_175829_6b96cd5d | 2026-05-20 17:58 |
| 20260520_180704_d61ca247 | 2026-05-20 18:07 |
| 20260520_180706_62466ba9 | 2026-05-20 18:07 |
| 20260520_180720_618a6bf9 | 2026-05-20 18:07 |
| 20260520_180726_52ff402e | 2026-05-20 18:07 |
| 20260520_180742_8228c308 | 2026-05-20 18:07 |
| 20260520_181202_cc74fb52 | 2026-05-20 18:12 |
| 20260520_181443_55d0cba9 | 2026-05-20 18:14 |
| 20260520_181520_f0e34370 | 2026-05-20 18:15 |
| 20260520_181636_bd89f09c | 2026-05-20 18:16 |
| 20260520_181652_bdd2c0bd | 2026-05-20 18:16 |
| 20260520_181812_62fa2ff2 | 2026-05-20 18:18 |
| 20260520_182103_86367165 | 2026-05-20 18:21 |
| 20260520_182504_5b89aa33 | 2026-05-20 18:25 |
| 20260520_182536_2b2d2aa7 | 2026-05-20 18:25 |
| 20260520_182627_cb57a7ba | 2026-05-20 18:26 |
| 20260520_182724_d90a61d4 | 2026-05-20 18:27 |
| 20260520_182828_d63454d4 | 2026-05-20 18:28 |
| 20260520_183219_871e9252 | 2026-05-20 18:32 |
| 20260520_183346_b88f652c | 2026-05-20 18:33 |
| 20260520_183403_e4da13b6 | 2026-05-20 18:34 |
| 20260520_184929_d2cc3495 | 2026-05-20 18:49 |
| 20260520_185029_eec2233a | 2026-05-20 18:50 |
| 20260520_185114_4fb577e8 | 2026-05-20 18:51 |
| 20260520_190248_cabc398b | 2026-05-20 19:02 |
| 20260520_190646_00a30704 | 2026-05-20 19:06 |
| 20260520_190713_13d7cecc | 2026-05-20 19:07 |
| 20260520_191749_4c518e55 | 2026-05-20 19:17 |

## Decisions made

- (None — all noise)

## Corrections / discoveries

- (None — all noise)

## Lessons learnt

- **Hermes captures raw SeaTalk webhook payloads as sessions** — these are shell-based sessions triggered by Hermes's own Docker/webhook bridge setup, not by user interaction. They should be filtered or grouped as stubs in reflect processing.

## Good patterns observed

- (None)

## What I learned about the user

- (None)

## Proposed updates

- Consider filtering Hermes session processing to skip sessions with < 3 turns or sessions that only contain webhook payload text (if possible)
