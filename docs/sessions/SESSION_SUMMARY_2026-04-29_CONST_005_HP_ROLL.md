# Session Summary — 2026-04-29 — `const.c` CONST-005 (advance_level HP roll + con_app)

## Scope

Closed the fourth `const.c` gap — `CONST-005`. ROM `src/update.c:74-79` rolls
`number_range(class.hp_min, class.hp_max) + con_app[CON].hitp` per level, then
`* 9 / 10` (C int div), then `UMAX(2, ...)`. The Python `advance_level` had
been using a static `LEVEL_BONUS[ch_class]` HP value with no RNG roll and no
CON modifier. Both halves are now ported.

## Outcomes

### `CONST-005` — ✅ FIXED

- **Python**: `mud/math/stat_apps.py::CON_APP` + `con_hitp_bonus`,
  `mud/advancement.py::advance_level`
- **ROM C**: `src/const.c:850-878` (table) + `src/update.c:74-79` (consumer);
  `class_table.hp_min/hp_max` already present on `ClassType` from prior port
- **Gap**: `CONST-005` — Per-level HP gain used static `LEVEL_BONUS[ch_class]`
  only; ROM rolls `number_range(class.hp_min, class.hp_max) + con_app[CON].hitp`,
  then `* 9 / 10`, then floor at 2.
- **Fix**:
  - New `CON_APP[26]` (full 2-column `hitp` + `shock`) verbatim port of
    `src/const.c:850-878` in `mud/math/stat_apps.py`. Note: ROM never reads
    the `shock` column (audit confirmed zero consumers); ported for table
    fidelity, not behavior.
  - New `con_hitp_bonus(ch) -> int` accessor reads
    `CON_APP[get_curr_stat(STAT_CON)].hitp`.
  - `mud/advancement.py::advance_level` HP path rewritten:
    `hp_roll = rng_mm.number_range(cls.hp_min, cls.hp_max)`,
    `add_hp = con_hitp_bonus(char) + hp_roll`,
    `add_hp = c_div(add_hp * 9, 10)`,
    `hp = max(2, add_hp)`. Mana/move/practices stay on legacy `LEVEL_BONUS`
    until CONST-006 (practices) and the separate mana/move RNG-roll gaps land.
- **Tests**: 14 new cases in `tests/integration/test_advancement_con_app.py` —
  table verification (5 parametrized class+CON combinations), HP-roll bounds,
  CON modifier application, `UMAX(2, …)` floor, `get_curr_stat` respects
  buffs (mod_stat), perm_hit tracking, played-time accounting still correct.
  6 existing tests in `tests/test_advancement.py` and
  `tests/integration/test_character_advancement.py` updated to seed
  `rng_mm.number_range` and assert the ROM formula (per AGENTS.md
  "a test asserting behavior that contradicts ROM C is a bug in the test").

## Files Modified

- `mud/math/stat_apps.py` — added `ConAppRow`, `CON_APP[26]`, `_curr_con`,
  `con_hitp_bonus(ch)`.
- `mud/advancement.py` — `advance_level` HP path now uses ROM RNG roll +
  `con_app[CON].hitp` + `* 9 / 10` + `UMAX(2, …)`.
- `tests/integration/test_advancement_con_app.py` — new file, 14 cases.
- `tests/test_advancement.py` — updated 2 cases to seed RNG and assert ROM HP.
- `tests/integration/test_character_advancement.py` — updated 5 cases (added
  `_rom_hp_gain` helper); seeds RNG and asserts ROM HP per level.
- `docs/parity/CONST_C_AUDIT.md` — flipped Phase 1 inventory row for
  `con_app[26]` from ❌ MISSING → ✅ AUDITED; flipped `CONST-005` row → ✅ FIXED.
- `CHANGELOG.md` — added `### Fixed` `CONST-005` entry under `[Unreleased]`.
- `pyproject.toml` — 2.6.50 → 2.6.51 (patch bump, this handoff commit).

## Test Status

- `pytest tests/integration/test_advancement_con_app.py` — 14 / 14 passing.
- `pytest tests/integration/ tests/test_advancement.py` — green; full session
  reported 1474 passed / 10 skipped (no regressions; 7 advancement tests that
  asserted the old static HP were updated, not bypassed).
- `ruff check mud/math/stat_apps.py mud/advancement.py
  tests/integration/test_advancement_con_app.py` — clean.

## Next Steps

Last `const.c` advancement gap before flipping the file row to ✅ Audited:

1. **`CONST-006`** (IMPORTANT) — `advance_level` per-level practice gain is
   constant `PRACTICES_PER_LEVEL = 1`; ROM uses `wis_app[WIS].practice` from
   `src/const.c:790-817` (single-column table). WIS-25 player currently
   misses +5 practices/level. Pairs cleanly with CONST-005 (same function,
   adjacent table). The integration test should parametrize across WIS values
   and assert `practice += wis_app[WIS].practice` (no RNG, no `c_div`).

After CONST-006 closes, flip `const.c` row in
`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` from ⚠️ Partial 80% → ✅ Audited
(CONST-001 stays parked for NANNY-009; CONST-007 stays parked for OLC). Same
commit must refresh README parity badges and AGENTS.md tracker pointers per
Repo Hygiene §2.

Continuing this session with `/rom-gap-closer CONST-006`.
