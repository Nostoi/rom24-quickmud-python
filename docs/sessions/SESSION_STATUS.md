# Session Status — 2026-07-16 — FIGHT-098 closed (area-attack char_list domain)

## Current State

- **Active focus**: cross-file invariants / divergence-class probe mode,
  running as an autonomous 10-iteration loop (iteration 2 complete).
- **Last completed**: **FIGHT-098 ✅ FIXED** (commit `dee59869`, v2.14.324) —
  `mob_hit`'s OFF_AREA_ATTACK sweep now walks ROM's global char_list domain
  from the room-head seed (`src/fight.c:262-270`), via the shared
  `char_list_walk_from_room_head` helper promoted from FIGHT-095's assist.py
  code. Iteration 1 closed **DB-005** (`29e9f99d`, v2.14.323 — reset
  processing per-room ascending room-vnum).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_FIGHT098_AREA_ATTACK_DOMAIN.md](SESSION_SUMMARY_2026-07-16_FIGHT098_AREA_ATTACK_DOMAIN.md)
- **Prior sessions (same date)**:
  [SESSION_SUMMARY_2026-07-16_DB005_RESET_ORDER_CLOSED.md](SESSION_SUMMARY_2026-07-16_DB005_RESET_ORDER_CLOSED.md),
  [SESSION_SUMMARY_2026-07-16_FIGHT095_CLOSED_DB005_FILED.md](SESSION_SUMMARY_2026-07-16_FIGHT095_CLOSED_DB005_FILED.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.324 |
| Tests | **6222 passed, 4 skipped, 0 failed** — clean full parallel run (243s). (+3 vs prior 6219: FIGHT-098 domain tests.) |
| ROM C files audited | 43 / 43 |
| Differential harness | 98/98 across 65 scenarios convergent |
| Push status | **Local only** — 2 gap commits + 1 docs commit this loop (`29e9f99d`, `b606303c`, `dee59869`) on top of prior same-date local commits; operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe (autonomous loop, 2/10) |

## Outstanding — deferred by design

- **GL-050** (OPEN) — `aggr_update` victim selection with 2 PCs in room; repro
  shape recorded in the row. Probe before fixing.
- **HANDLER-009** (OPEN, test-only) — `MobInstance.move_to_room` tail-append.
- **C-oracle scenarios** (deferred) — DB-005 `__mob_census` over `valley.are`
  and a FIGHT-098 OFF_AREA_ATTACK scenario both need the instrumented C binary;
  author in a C-capture-enabled session.
- Carry-overs: FIGHT-094 (`check_killer` placement), DESC-001, OLC spell-name
  lookup, IS_BUILDER, stray `data/quickmud.db` / `doc/game.db` cleanup.

## Next Intended Task

**GL-050** — probe `aggr_update` victim selection with 2 PCs in a room against
ROM `src/update.c` (or `fight.c`) ground truth: read the C, read the Python,
write one failing contract test, then close as a gap or file as an INV. If the
probe shows it needs the C oracle, fall back to HANDLER-009 (test-only,
well-scoped).
