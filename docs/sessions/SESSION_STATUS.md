# Session Status — 2026-07-16 — DB-005 closed (reset order: per-room ascending room-vnum)

## Current State

- **Active focus**: cross-file invariants / divergence-class probe mode,
  running as an autonomous 10-iteration loop (iteration 1 complete).
- **Last completed**: **DB-005 ✅ FIXED** (commit `29e9f99d`, v2.14.323) —
  `apply_resets` now buckets resets per owning room (mirroring ROM
  `load_resets` rVnum tracking) and processes rooms ascending by vnum, with
  `LastMob`/`LastObj` state reset at room boundaries (ROM `reset_room`
  locals). Fixes world population where global M-limits bind mid-area
  (valley.are 7803: 3 sentries, not 4) and boot creation order
  (`char_list` order for INV-045 newest-first walks).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_DB005_RESET_ORDER_CLOSED.md](SESSION_SUMMARY_2026-07-16_DB005_RESET_ORDER_CLOSED.md)
- **Prior sessions (same date)**:
  [SESSION_SUMMARY_2026-07-16_FIGHT095_CLOSED_DB005_FILED.md](SESSION_SUMMARY_2026-07-16_FIGHT095_CLOSED_DB005_FILED.md),
  [SESSION_SUMMARY_2026-07-16_FOLLOWER_DISBAND_SWEEP_FIGHT095_DERISK.md](SESSION_SUMMARY_2026-07-16_FOLLOWER_DISBAND_SWEEP_FIGHT095_DERISK.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.323 |
| Tests | **6219 passed, 4 skipped, 0 failed** — clean full parallel run (286s). (+1 vs prior 6218: DB-005 regression test.) |
| ROM C files audited | 43 / 43 |
| Differential harness | 98/98 across 65 scenarios convergent |
| Push status | **Local only** — 1 commit this iteration (`29e9f99d`) on top of 14 prior same-date local commits; operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe (autonomous loop) |

## Outstanding — deferred by design

- **FIGHT-098** (OPEN) — `mob_hit` OFF_AREA_ATTACK sweep, sibling of FIGHT-095
  (fix pattern proven). Needs its own C-oracle scenario.
- **GL-050** (OPEN) — `aggr_update` victim selection with 2 PCs in room; repro
  shape recorded in the row. Probe before fixing.
- **HANDLER-009** (OPEN, test-only) — `MobInstance.move_to_room` tail-append.
- **DB-005 diff-harness scenario** (deferred) — `__mob_census` scenario over
  `valley.are` needs the instrumented C binary for golden capture; author in a
  C-capture-enabled session.
- Carry-overs: FIGHT-094 (`check_killer` placement), DESC-001, OLC spell-name
  lookup, IS_BUILDER, stray `data/quickmud.db` / `doc/game.db` cleanup.

## Next Intended Task

**FIGHT-098** — `mob_hit` OFF_AREA_ATTACK sweep. Sibling of FIGHT-095 (the
global-`char_list`-domain fix pattern is proven); read ROM `src/fight.c`
`mob_hit`'s area-attack walk, write the failing domain test, and close via
`/rom-gap-closer FIGHT-098`. If blocked on C-oracle needs, fall back to
GL-050's probe.
