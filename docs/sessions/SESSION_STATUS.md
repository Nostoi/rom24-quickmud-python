# Session Status — 2026-07-16 — GL-050 closed + FIGHT-099 link-dead recall fixed

## Current State

- **Active focus**: cross-file invariants / divergence-class probe mode,
  running as an autonomous 10-iteration loop (iteration 3 complete).
- **Last completed**: **GL-050 ✅ CLOSED** (aggr_update verified faithful; the
  observed victim flip was DB-005 contamination) + **FIGHT-099 ✅ FIXED**
  (link-dead PC auto-recall in `damage()`'s epilogue, `src/fight.c:978-991`) —
  commit `e2ba759d`, v2.14.325, locked by new C-oracle scenario
  `aggr_two_pc_victim_selection` (99/99 differential). **FIGHT-100 filed
  OPEN** (wimpy auto-flee legs, `fight.c:993-1012`). Loop history: iter 1
  DB-005 (`29e9f99d`), iter 2 FIGHT-098 (`dee59869`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_GL050_PROBE_FIGHT099_LINKDEAD_RECALL.md](SESSION_SUMMARY_2026-07-16_GL050_PROBE_FIGHT099_LINKDEAD_RECALL.md)
- **Prior sessions (same date)**:
  [SESSION_SUMMARY_2026-07-16_FIGHT098_AREA_ATTACK_DOMAIN.md](SESSION_SUMMARY_2026-07-16_FIGHT098_AREA_ATTACK_DOMAIN.md),
  [SESSION_SUMMARY_2026-07-16_DB005_RESET_ORDER_CLOSED.md](SESSION_SUMMARY_2026-07-16_DB005_RESET_ORDER_CLOSED.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.325 |
| Tests | **6227 passed, 4 skipped, 0 failed** (unit 2798 + integration 3429; layers run separately due to an intermittent xdist worker-crash INTERNALERROR on full runs — infra flake, no test failures). (+5 vs prior 6222: FIGHT-099 ×4, differential ×1.) |
| ROM C files audited | 43 / 43 |
| Differential harness | 99/99 across 66 scenarios convergent |
| Push status | **Local only** — loop commits `29e9f99d`, `b606303c`, `dee59869`, `b229b8e9`, `e2ba759d`; operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe (autonomous loop, 3/10) |

## Outstanding — deferred by design

- **FIGHT-100** (OPEN) — wimpy auto-flee legs of damage()'s epilogue
  (`src/fight.c:993-1012`): NPC wimpy/charm flee + PC `hit <= wimpy` flee.
  RNG-bearing; fix pattern established by FIGHT-099. Route:
  `/rom-gap-closer FIGHT-100`.
- **HANDLER-009** (OPEN, test-only) — `MobInstance.move_to_room` tail-append.
- **C-oracle scenarios** (deferred) — DB-005 `__mob_census` over `valley.are`;
  a FIGHT-098 OFF_AREA_ATTACK scenario. The C binary (`src/diffshim`) is
  built and working — these are now unblocked.
- Carry-overs: FIGHT-094 (`check_killer` placement), DESC-001, OLC spell-name
  lookup, IS_BUILDER, stray `data/quickmud.db` / `doc/game.db` cleanup.

## Next Intended Task

**FIGHT-100** — close the wimpy auto-flee legs via `/rom-gap-closer
FIGHT-100`: read ROM `src/fight.c:993-1012` + `do_flee`, failing test first
(NPC wimpy flee at low hp; PC `hit <= wimpy` flee; both gated on
`wait < PULSE_VIOLENCE / 2`), ideally locked with a C-oracle wimpy scenario.
