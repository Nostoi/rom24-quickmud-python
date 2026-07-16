# Session Status — 2026-07-16 — FIGHT-095 closed (check_assist char_list domain) + DB-005 filed

## Current State

- **Active focus**: cross-file invariants / divergence-class probe mode.
  User-commissioned `/rom-gap-closer FIGHT-095` completed this session.
- **This run (v2.14.319 → v2.14.322):** 3 gaps fixed, 3 filed.
  - **FIGHT-095 ✅ FIXED** — `check_assist`'s NPC-assist reservoir now walks
    ROM's global `char_list` domain (reversed registry slice from room-head,
    INV-045/GROUP-006 pattern). C-oracle locked: new differential scenario
    `check_assist_cross_room` + 8-seed `__rng_probe` alignment sweep +
    3 C-independent domain tests. Commit `79d90e64`.
  - **FIGHT-096 ✅** (assist emote act-render, `41cf0c77`) and **FIGHT-097 ✅**
    (`attack_round` one_hit self/dead/cross-room zero-RNG guards, `733a460b`) —
    convergence prerequisites surfaced by the C capture.
  - **DB-005 ⚠️ FILED (HIGH)** — Python applies area resets in FILE order; ROM
    `reset_area` iterates rooms ascending-vnum. Boot population (valley.are mob
    7803: 4 vs 3) and boot creation order diverge (world-level INV-045
    exposure). Found by draw-count forensics vs the live C oracle
    (`__mob_census`). Also filed: GL-050 (aggr victim selection, needs probe),
    HANDLER-009 (test-only move_to_room tail-append), FIGHT-098 (sibling walk).
  - **Harness**: six new C+Python directives (`__char_goto`, `__mob_off_flags`,
    `__mob_add_affect`, `__rng_probe`, `__sneak_census`, `__mob_census`);
    differential suite now 98 tests / 65 scenarios.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_FIGHT095_CLOSED_DB005_FILED.md](SESSION_SUMMARY_2026-07-16_FIGHT095_CLOSED_DB005_FILED.md)
- **Prior sessions (same date)**:
  [SESSION_SUMMARY_2026-07-16_FOLLOWER_DISBAND_SWEEP_FIGHT095_DERISK.md](SESSION_SUMMARY_2026-07-16_FOLLOWER_DISBAND_SWEEP_FIGHT095_DERISK.md),
  [SESSION_SUMMARY_2026-07-16_EXTRACT_CLEANUP_MATRIX_DIVERGENCE_SWEEP.md](SESSION_SUMMARY_2026-07-16_EXTRACT_CLEANUP_MATRIX_DIVERGENCE_SWEEP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.322 |
| Tests | **6218 passed, 4 skipped, 0 failed** — clean complete parallel run (487s). (+9 vs prior 6209: FIGHT-095×3, 096×2, 097×3, +1 differential.) |
| ROM C files audited | 43 / 43 |
| Differential harness | 98/98 across 65 scenarios convergent |
| Push status | **Local only** — 3 commits this run (`41cf0c77`, `733a460b`, `79d90e64`) on top of 10 prior same-date local commits; operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe |

## Outstanding — deferred by design

- **DB-005** (OPEN, **HIGH**) — reset processing order: file order vs ROM's
  per-room ascending-vnum. World population + boot creation order diverge.
  Exact repro (`valley.are` 7803, `__mob_census`) + fix direction in
  `DB_C_AUDIT.md`. Reset-engine blast radius — expect test/golden fallout
  triage. Route: `/rom-gap-closer DB-005`.
- **FIGHT-098** (OPEN) — `mob_hit` OFF_AREA_ATTACK sweep, sibling of FIGHT-095
  (fix pattern proven). Needs its own C-oracle scenario.
- **GL-050** (OPEN) — `aggr_update` victim selection with 2 PCs in room; repro
  shape recorded in the row. Probe before fixing.
- **HANDLER-009** (OPEN, test-only) — `MobInstance.move_to_room` tail-append.
- Carry-overs: FIGHT-094 (`check_killer` placement), DESC-001, OLC spell-name
  lookup, IS_BUILDER, stray `data/quickmud.db` / `doc/game.db` cleanup.

## Next Intended Task

**DB-005** — the highest-value open gap (boot-world parity; everything
downstream of world population inherits it). Dedicated session: mirror
`reset_area`/`reset_room` per-room ascending-vnum processing in
`reset_handler.apply_resets`, lock with a `__mob_census` diff-harness scenario
over `valley.are`, and triage test/golden fallout (some tests may encode
file-order populations).
