# Session Status — 2026-04-29 — `const.c` CONST-004 Closed (combat-math triplet 3/3 ✅)

## Current State

- **Active audit**: `const.c` (Phase 4 — combat-math triplet complete; advancement gaps remain).
- **Last completed**: `CONST-004` (`GET_AC` adds `dex_app[DEX].defensive` with `IS_AWAKE` gate; new `DEX_APP[26]` table + `get_ac` accessor in `mud/math/stat_apps.py`; combat + score + wiz "stat char" AC reads all wired through it). Commit `4fcfb23`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-29_CONST_004_GET_AC.md](SESSION_SUMMARY_2026-04-29_CONST_004_GET_AC.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.50 |
| Tests | 1569 passing / 10 skipped (full integration + combat suite). 1 pre-existing unit-suite failure in `test_area_loader.py` unrelated to combat. |
| ROM C files audited | 18 / 43 (42%) ✅ Audited; `const.c` ⚠️ Partial 80% (1 CRITICAL + 2 IMPORTANT + 1 MINOR open: CONST-005, CONST-006, CONST-001 deferred to NANNY-009, CONST-007 deferred to OLC). |
| Active focus | `const.c` — advancement gaps next (CONST-005 + CONST-006). |

## Next Intended Task

**`CONST-005`** (CRITICAL) — `advance_level` per-level HP gain. Currently uses static `LEVEL_BONUS[ch_class]` in `mud/advancement.py:91`; ROM `src/update.c:74-79` rolls `number_range(class_table.hp_min, class_table.hp_max) + con_app[CON].hitp`.

Pre-flight checks before writing the test:

1. Read `mud/advancement.py:advance_level` end-to-end against `src/update.c:30-150`.
2. Verify `class_table.hp_min` and `hp_max` are present on `mud/models/classes.py:ClassType`. If absent, port them from `src/const.c:394-419` (4-class table) **as a separate sub-step inside this gap** — they're prerequisite data, not a separate gap.
3. Port `con_app[26]` (single column `hitp`; ROM also defines `shock` but it's dead data per the audit — verified by grep on `src/`) into `mud/math/stat_apps.py` as `CON_APP`. Add `_curr_con(ch)` helper using the existing `_curr_stat`.
4. Decide accessor shape — likely `con_hitp_bonus(ch) -> int` rather than a full `get_max_hit_gain` since the RNG roll lives in `advance_level`, not in the table accessor.

Test: seed `rng_mm.seed_mm(<known seed>)` inside the test (overriding the autouse 12345), then assert exact HP gain for a high-CON vs low-CON character of the same class. Verify the difference equals `con_app[hi].hitp - con_app[lo].hitp` and that the base random component matches `number_range(class.hp_min, class.hp_max)`.

After CONST-005: **`CONST-006`** (`wis_app[WIS].practice` in `advance_level`; same function, single-column `wis_app` table from `src/const.c:790-817`).

After both close, flip `const.c` row in `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` from ⚠️ Partial 80% → ✅ Audited (CONST-001 parked for NANNY-009; CONST-007 parked for OLC).

Run `/rom-gap-closer CONST-005` to continue.
