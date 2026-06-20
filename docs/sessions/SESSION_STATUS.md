# Session Status — 2026-06-20 — interp.c cmd_table comprehensive sweep (/loop)

## Current State

- **Active focus**: Autonomous `/loop` gap-closer run ("close the next gap via
  `/rom-gap-closer`, repeat for 3 hours, then handoff"). Started ~04:35 local;
  **3-hour deadline ≈ 07:35 local (epoch 1781958898)**. Loop runs in-turn with
  `date` checks against that epoch (NOT ScheduleWakeup — the fixed `/loop` prompt
  would re-arm a fresh 3h window each fire and corrupt the deadline).
- **Theme**: systematic ROM↔Python table diffs. The entire `interp.c` `cmd_table`
  is now swept across **every field** with a parametrized anti-drift guard per
  field (mirroring how INTERP-001 closed the 43-row trust cluster as one commit +
  50-param guard). Static data tables spot/positionally diffed: `skill_table`
  (mana/beats) and `liq_table` confirmed clean.

### Closed this session (master, pushed through v2.14.194) — 9 commits

| Ver | ID | What |
|-----|-----|------|
| 2.14.187 | **INTERP-027** | `backstab` min_position STANDING→FIGHTING (fighting char reaches "You're facing the wrong end.") |
| — | (determinism) | seed `test_backstab_uses_position_and_weapon` against an un-monkeypatched `number_bits(5)` flake (failed under seed 12345; module is outside `tests/integration/` so no autouse seed) |
| 2.14.189 | **INTERP-029** | `recall` min_position STANDING→FIGHTING — combat-recall branch (`session.py:371`) was dead code |
| 2.14.190 | **INTERP-031** | `cast` min_position RESTING→FIGHTING (was too permissive; ROM requires standing) |
| 2.14.191 | **INTERP-030** | min-position cluster (10 cmds): comm channels RESTING→SLEEPING, quit/gtell SLEEPING→DEAD, murde DEAD→FIGHTING. 16-case guard |
| 2.14.192 | **INTERP-032** | show-flag cluster (5): rescue/rent/dump/invis hide, teleport show. 5-case guard |
| 2.14.193 | **INTERP-033** | log-flag cluster (39): **SECURITY** password/mob→LOG_NEVER, 36 admin cmds→LOG_ALWAYS, asave→NORMAL. 39-case guard |
| 2.14.194 | **INTERP-034** | **SECURITY (consumer)** LOG_NEVER now blanks logline unconditionally — password leaked to admin log + wiznet when global log-all was on (reproduced). `process_command` HIGH blast-radius but logging-only |

- **Full suite green after all 9**: `5979 passed, 4 skipped` (was 5916 at session
  start; +63 guard cases).

### Open / Outstanding

- **INTERP-028** (MINOR, 🔄 OPEN): duplicate `bs` registration (alias on
  `backstab` + standalone `Command("bs", do_bs, …)`). No observable divergence
  (COMMAND_INDEX["bs"] resolves identically) — cosmetic cleanup, left open.
- **Risk-posture rule for the rest of this loop** (per advisor): the easy
  data/registration veins are dry. Remaining gaps are behavioral. When a
  divergence needs logic changes in a HIGH-blast-radius core path
  (combat/movement/dispatch), **file it** (audit row + this Outstanding list),
  do NOT fix autonomously — leave for human-reviewed work. Only fix
  cleanly-isolated cases. Low-risk diff fuel still available: race/class stat
  tables, `mob_cmds`/`obj` command tables, `social_table` data, position/sex/size
  string tables.
- **Unverified negative**: skill_table mana/beats diff was a name-join; spot-
  checked 3 names + 135 parsed, but match-count not printed. Treat as suggestive,
  not a confirmed clean, until coverage is printed.

## Pointer to latest summary

This session's full summary will be written by `/rom-session-handoff` at loop end
(target ~07:35 local). Until then this STATUS is the canonical pointer.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.194 |
| Tests | 5979 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 |
| Active focus | `/loop` systematic table-diff gap-closing |

## Next Intended Task

Continue the loop in the low-risk systematic-diff lane (race/class stat tables,
mob/obj command tables, social_table data, string tables). File HIGH-risk
behavioral divergences instead of fixing. Run `/rom-session-handoff` at the
3-hour deadline.
