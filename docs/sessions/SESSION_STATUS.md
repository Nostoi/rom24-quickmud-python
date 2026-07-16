# Session Status — 2026-07-16 — FIGHT-094 closed (check_killer inside damage())

## Current State

- **Active focus**: cross-file invariants / divergence-class probe mode,
  running as an autonomous 10-iteration loop (iteration 8 complete).
- **Last completed**: **FIGHT-094 ✅ FIXED** (commit `0fe87f8f`, v2.14.330) —
  `check_killer` now runs inside `apply_damage` at ROM's position
  (`fight.c:733`, before set_fighting), making the first PvP hit PK-flag
  through ANY damage path. Loop history: iters 1-7 = DB-005, FIGHT-098,
  GL-050+FIGHT-099, FIGHT-100, FIGHT-101, FIGHT-102, scenario-batch+FIGHT-103.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_FIGHT094_DAMAGE_CHECK_KILLER.md](SESSION_SUMMARY_2026-07-16_FIGHT094_DAMAGE_CHECK_KILLER.md)
- **Prior sessions (same date)**:
  [SESSION_SUMMARY_2026-07-16_CORACLE_SCENARIO_BATCH_FIGHT103.md](SESSION_SUMMARY_2026-07-16_CORACLE_SCENARIO_BATCH_FIGHT103.md),
  [SESSION_SUMMARY_2026-07-16_FIGHT102_WAIT_GATE_SWEEP.md](SESSION_SUMMARY_2026-07-16_FIGHT102_WAIT_GATE_SWEEP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.330 |
| Tests | **6242 passed, 4 skipped, 0 failed** (unit 2801 + integration 3441; layers run separately — intermittent xdist worker-crash INTERNALERROR on single full runs is an infra flake). |
| ROM C files audited | 43 / 43 |
| Differential harness | 102/102 across 69 scenarios convergent |
| Push status | **Local only** — loop commits `29e9f99d`…`0fe87f8f` (16 total incl. docs); operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe (autonomous loop, 8/10) |

## Outstanding — deferred by design

- **HANDLER-009** (OPEN, test-only) — `MobInstance.move_to_room` tail-append
  (ROM `char_to_room` head-inserts). Best-scoped next item.
- Carry-overs: DESC-001, OLC spell-name lookup, IS_BUILDER, stray
  `data/quickmud.db` / `doc/game.db` cleanup.

## Next Intended Task

**HANDLER-009** — grep its row (likely `HANDLER_C_AUDIT.md`), read ROM
`char_to_room` (`src/handler.c`), fix `MobInstance.move_to_room`'s
tail-append to head-insert, close via `/rom-gap-closer HANDLER-009`. If it
falls through quickly, spend the remainder of the iteration on the stray
db-file cleanup or a divergence-class probe.
