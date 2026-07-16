# Session Status — 2026-07-16 — FIGHT-100 closed (wimpy auto-flee on damage)

## Current State

- **Active focus**: cross-file invariants / divergence-class probe mode,
  running as an autonomous 10-iteration loop (iteration 4 complete).
- **Last completed**: **FIGHT-100 ✅ FIXED** (commit `58c955f7`, v2.14.326) —
  wimpy auto-flee legs of `damage()`'s epilogue (`src/fight.c:993-1012`):
  NPC ACT_WIMPY low-hp flee, charmed-NPC absent-master flee, PC
  `hit <= wimpy` flee, all gated `wait < PULSE_VIOLENCE / 2`. **FIGHT-101
  filed OPEN** (do_flee's non-ROM wait-gate + WAIT_STATE). Loop history:
  iter 1 DB-005 (`29e9f99d`), iter 2 FIGHT-098 (`dee59869`), iter 3
  GL-050+FIGHT-099 (`e2ba759d`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_FIGHT100_WIMPY_AUTOFLEE.md](SESSION_SUMMARY_2026-07-16_FIGHT100_WIMPY_AUTOFLEE.md)
- **Prior sessions (same date)**:
  [SESSION_SUMMARY_2026-07-16_GL050_PROBE_FIGHT099_LINKDEAD_RECALL.md](SESSION_SUMMARY_2026-07-16_GL050_PROBE_FIGHT099_LINKDEAD_RECALL.md),
  [SESSION_SUMMARY_2026-07-16_FIGHT098_AREA_ATTACK_DOMAIN.md](SESSION_SUMMARY_2026-07-16_FIGHT098_AREA_ATTACK_DOMAIN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.326 |
| Tests | **6232 passed, 4 skipped, 0 failed** (unit 2798 + integration 3434, layers run separately — intermittent xdist worker-crash INTERNALERROR on single full runs is an infra flake). (+5 vs prior 6227: FIGHT-100 tests.) |
| ROM C files audited | 43 / 43 |
| Differential harness | 99/99 across 66 scenarios convergent |
| Push status | **Local only** — loop commits `29e9f99d`, `b606303c`, `dee59869`, `b229b8e9`, `e2ba759d`, `47d075fb`, `58c955f7`; operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe (autonomous loop, 4/10) |

## Outstanding — deferred by design

- **FIGHT-101** (OPEN) — Python `do_flee` non-ROM wait-gate + WAIT_STATE
  (ROM `do_flee` has neither, `src/fight.c:2970-3030`). Verify first whether
  the command dispatcher separately enforces wait (double-counting) before
  removing. Route: `/rom-gap-closer FIGHT-101`.
- **HANDLER-009** (OPEN, test-only) — `MobInstance.move_to_room` tail-append.
- **C-oracle scenarios** (deferred, unblocked — `src/diffshim` works) —
  DB-005 `__mob_census` over `valley.are`; FIGHT-098 OFF_AREA_ATTACK;
  a FIGHT-100 wimpy-flee scenario.
- Carry-overs: FIGHT-094 (`check_killer` placement), DESC-001, OLC spell-name
  lookup, IS_BUILDER, stray `data/quickmud.db` / `doc/game.db` cleanup.

## Next Intended Task

**FIGHT-101** — probe-then-close: read `mud/commands/dispatcher.py`'s wait
handling to establish whether do_flee's internal gate double-counts ROM's
interpreter wait; read ROM `interp.c` wait semantics; then either delete the
gate+lag (ROM-faithful) or document the architectural compensation and close
the row with a citation. Failing test: wimpy auto-flee at wait 1..5 (blocked
today, ROM flees).
