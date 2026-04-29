# Session Status — 2026-04-29 — `const.c` CONST-005 Closed (HP roll + con_app)

## Current State

- **Active audit**: `const.c` (Phase 4 — advancement gaps; only CONST-006 remains before file flips to ✅ Audited).
- **Last completed**: `CONST-005` (`advance_level` HP path now rolls `number_range(class.hp_min, class.hp_max) + con_app[CON].hitp`, `* 9 / 10` (c_div), `UMAX(2, …)`; `CON_APP[26]` ported into `mud/math/stat_apps.py` with `con_hitp_bonus(ch)` accessor). Commit `d60151e`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-29_CONST_005_HP_ROLL.md](SESSION_SUMMARY_2026-04-29_CONST_005_HP_ROLL.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.51 |
| Tests | 1474 passed / 10 skipped (no regressions; 7 advancement tests updated to seed RNG and assert ROM HP formula per AGENTS.md "test contradicting ROM is a bug in the test"). |
| ROM C files audited | 18 / 43 (42%) ✅ Audited; `const.c` ⚠️ Partial 90% (1 IMPORTANT open: CONST-006; CONST-001 deferred to NANNY-009; CONST-007 deferred to OLC). |
| Active focus | `const.c` — CONST-006 last advancement gap before file flip. |

## Next Intended Task

**`CONST-006`** (IMPORTANT) — `advance_level` per-level practice gain. Currently constant `PRACTICES_PER_LEVEL = 1` in `mud/advancement.py`; ROM `src/update.c:87` uses `wis_app[WIS].practice` from the single-column table `src/const.c:790-817`. WIS-25 player currently misses +5 practices/level.

Pre-flight checks before writing the test:

1. Read `src/const.c:790-817` and confirm the column shape (single int per row). The table follows immediately after `int_app` in `const.c`.
2. Read `src/update.c:80-100` to confirm `advance_level` adds `wis_app[GET_WIS(ch)].practice` to `ch->practice`.
3. Add `WIS_APP[26]` (single column) into `mud/math/stat_apps.py` next to the existing tables. Add `wis_practice_bonus(ch) -> int` accessor (or pattern matching `con_hitp_bonus`).
4. Replace the `char.practice += PRACTICES_PER_LEVEL` line in `mud/advancement.py::advance_level` with `char.practice += wis_practice_bonus(char)`. Update the user-facing "You gain … N practice(s)" message to reflect the actual roll (the existing pluralization helper already handles this).

Test: parametrize across WIS values, assert `practice += wis_app[WIS].practice`. No RNG involved (purely table-driven).

After CONST-006 closes, flip `const.c` row in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` from ⚠️ Partial 90% → ✅ Audited (CONST-001 parked for NANNY-009; CONST-007 parked for OLC). Same commit must refresh README parity badges and AGENTS.md tracker pointers per Repo Hygiene §2.

Run `/rom-gap-closer CONST-006` to continue.
