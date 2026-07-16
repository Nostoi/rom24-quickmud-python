# Session Status — 2026-07-16 — FIGHT-101 closed (do_flee wait-gate/lag removed)

## Current State

- **Active focus**: cross-file invariants / divergence-class probe mode,
  running as an autonomous 10-iteration loop (iteration 5 complete — halfway).
- **Last completed**: **FIGHT-101 ✅ FIXED** (commit `93fcba45`, v2.14.327) —
  `do_flee`'s non-ROM wait-gate + WAIT_STATE removed; ROM enforces wait at
  the descriptor loop (already mirrored by `mud/net/connection.py`), and
  direct dispatch bypasses it. **FIGHT-102 filed OPEN** (six sibling command
  gates, per-site ROM read needed). Loop history: iter 1 DB-005, iter 2
  FIGHT-098, iter 3 GL-050+FIGHT-099, iter 4 FIGHT-100.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_FIGHT101_FLEE_WAIT_GATE.md](SESSION_SUMMARY_2026-07-16_FIGHT101_FLEE_WAIT_GATE.md)
- **Prior sessions (same date)**:
  [SESSION_SUMMARY_2026-07-16_FIGHT100_WIMPY_AUTOFLEE.md](SESSION_SUMMARY_2026-07-16_FIGHT100_WIMPY_AUTOFLEE.md),
  [SESSION_SUMMARY_2026-07-16_GL050_PROBE_FIGHT099_LINKDEAD_RECALL.md](SESSION_SUMMARY_2026-07-16_GL050_PROBE_FIGHT099_LINKDEAD_RECALL.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.327 |
| Tests | **6234 passed, 4 skipped, 0 failed** (unit 2798 + integration 3436, layers run separately — intermittent xdist worker-crash INTERNALERROR on single full runs is an infra flake). (+2 vs prior 6232.) |
| ROM C files audited | 43 / 43 |
| Differential harness | 99/99 across 66 scenarios convergent |
| Push status | **Local only** — loop commits `29e9f99d`…`93fcba45` (9 total incl. docs); operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe (autonomous loop, 5/10) |

## Outstanding — deferred by design

- **FIGHT-102** (OPEN) — six sibling non-ROM wait-gates (`do_kick`,
  `do_rescue`, `do_backstab`, `do_bash`, `do_berserk`, `do_cast`). Per-site
  ROM read before removal (mob_hit's `wait > 0` guard covers NPC off-skill
  dispatch; verify each caller). Route: `/rom-gap-closer FIGHT-102`.
- **HANDLER-009** (OPEN, test-only) — `MobInstance.move_to_room` tail-append.
- **C-oracle scenarios** (deferred, unblocked) — DB-005 `__mob_census`;
  FIGHT-098 OFF_AREA_ATTACK; FIGHT-100 wimpy-flee.
- Carry-overs: FIGHT-094 (`check_killer` placement), DESC-001, OLC spell-name
  lookup, IS_BUILDER, stray `data/quickmud.db` / `doc/game.db` cleanup.

## Next Intended Task

**FIGHT-102** — sweep the six sibling wait-gates: for each command, read the
ROM function top-to-bottom (does ROM itself gate on anything wait-adjacent?),
check every Python direct-dispatch caller, remove the gate where ROM has
none, keep/adjust where ROM has its own logic. One test per removed gate
(direct-dispatch executes at wait>0), single commit if closed as one class —
or split per command if behaviors diverge.
