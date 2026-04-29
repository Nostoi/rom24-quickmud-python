# Session Summary — 2026-04-29 — `const.c` CONST-006 (advance_level wis_app practice) + file flip ✅

## Scope

Closed the last in-scope `const.c` gap — `CONST-006`. ROM `src/update.c:87`
applies `add_prac = wis_app[get_curr_stat(ch, STAT_WIS)].practice;
ch->practice += add_prac;`. Python had been using a hardcoded
`PRACTICES_PER_LEVEL = 2` constant. With CONST-006 closed, all five
behavioral `const.c` gaps (CONST-002..006) are fixed; the file flips
⚠️ Partial 90% → ✅ Audited 95%. The 5% gap is the two intentionally
deferred items: CONST-001 (`title_table`, 480 entries) parked for the
NANNY-009 dedicated session, and CONST-007 (`weapon_table`) parked for
the OLC audit.

## Outcomes

### `CONST-006` — ✅ FIXED

- **Python**: `mud/math/stat_apps.py::WIS_APP` + `wis_practice_bonus`,
  `mud/advancement.py::advance_level`
- **ROM C**: `src/const.c:790-817` (table) + `src/update.c:87` (consumer)
- **Gap**: `CONST-006` — Per-level practice gain was a constant
  `PRACTICES_PER_LEVEL = 2`. ROM applies `wis_app[WIS].practice`: 0 for
  WIS 0–4, 1 for WIS 5–14, 2 for WIS 15–17, 3 for WIS 18–21, 4 for WIS
  22–24, 5 for WIS 25. WIS-3 was getting +2 free practices/level
  instead of 0; WIS-25 sage was getting 2 instead of 5.
- **Fix**:
  - New `WIS_APP[26]` (single-column `practice`) verbatim port of
    `src/const.c:790-817` in `mud/math/stat_apps.py`.
  - New `wis_practice_bonus(ch) -> int` accessor reads
    `WIS_APP[get_curr_stat(STAT_WIS)].practice`.
  - `mud/advancement.py::advance_level` replaces the constant
    `PRACTICES_PER_LEVEL` line with `practice_gain = wis_practice_bonus(char)`
    and uses that in both the stat update and the user-facing message.
    The pluralisation now correctly handles 0/1/N (e.g. "1 practice"
    singular vs "5 practices" plural, including "0 practices").
- **Tests**: 26 new cases in `tests/integration/test_advancement_wis_app.py`
  — table verification (13 parametrized WIS values), `wis_practice_bonus`
  reading current stat, mod_stat buff respect, `advance_level` per-WIS
  practice gain (4 parametrized WIS values), level-up message reflects
  actual gain with correct pluralisation, train counter unchanged
  (still constant 1). 5 existing tests in `tests/test_advancement.py`
  and `tests/integration/test_character_advancement.py` updated from
  the old `+2 practices/level` constant assertions to ROM's
  `wis_app[WIS].practice` formula (per AGENTS.md "test asserting
  behavior contradicting ROM is a bug in the test").

### `const.c` file row — ✅ AUDITED (90% → 95%)

- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` row flipped
  ⚠️ Partial 80% → ✅ Audited 95%.
- 16/16 tables now ✅ AUDITED (full ports of `str_app`, `dex_app`,
  `con_app`, `wis_app`, `int_app`, `liq_table`, `skill_table`,
  `group_table`, `item_table`, `wiznet_table`, `attack_table`,
  `race_table`, `pc_race_table`, `class_table`).
- 5/7 gaps closed (CONST-002..006). Remaining 2 are deferred-by-design,
  not in-scope for this file:
  - **CONST-001** `title_table` (480 entries) — defer to NANNY-009
    dedicated session.
  - **CONST-007** `weapon_table` (8 entries, BIT-style data) — defer to
    OLC audit.

## Files Modified

- `mud/math/stat_apps.py` — added `WisAppRow`, `WIS_APP[26]`, `_curr_wis`,
  `wis_practice_bonus(ch)`.
- `mud/advancement.py` — `advance_level` practice gain now reads
  `wis_practice_bonus(char)`; level-up message reflects actual roll.
- `tests/integration/test_advancement_wis_app.py` — new file, 26 cases.
- `tests/test_advancement.py` — updated 2 cases to assert ROM's
  `wis_app` formula (1 practice for WIS-13 mage; "1 practice" singular).
- `tests/integration/test_character_advancement.py` — updated 3 cases
  to assert ROM's `wis_app` formula (`+1 practice/level` for WIS-13
  default rather than the old `+2`).
- `docs/parity/CONST_C_AUDIT.md` — flipped Phase 1 inventory row for
  `wis_app[26]` from ❌ MISSING → ✅ AUDITED; flipped `CONST-006` row
  → ✅ FIXED.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — flipped `const.c` row
  ⚠️ Partial 80% → ✅ Audited 95%.
- `CHANGELOG.md` — added `### Fixed` `CONST-006` entry under `[Unreleased]`.
- `pyproject.toml` — 2.6.51 → 2.6.52 (patch bump, this handoff commit).

## Test Status

- `pytest tests/integration/test_advancement_wis_app.py` — 26 / 26 passing.
- `pytest tests/integration/` — 1455 passed / 10 skipped (no regressions;
  5 advancement tests that asserted the old constant practice gain were
  updated to the ROM formula, not bypassed).
- `ruff check mud/math/stat_apps.py mud/advancement.py
  tests/integration/test_advancement_wis_app.py
  tests/test_advancement.py
  tests/integration/test_character_advancement.py` — clean
  (auto-fixed import order on the test files).

## Next Steps

`const.c` is now ✅ Audited. Next file off the **P3 utilities & helpers**
group in `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`. Likely candidates depending
on priority queue:

1. **`recycle.c`** (P3) — currently ⚠️ Partial. Buffer / object / mob /
   character pool plumbing. Most behavioral consequences land in the
   pool-reuse paths.
2. **`tables.c`** is already ✅ Audited. **`lookup.c`** is ✅ Audited.
3. Otherwise, picking up the next P0/P1 row (combat or act_*).

The README "ROM C Source Audit: 13 of 43" line is stale — actual count
should be 19/43 with const.c just flipped. A coordinated README +
AGENTS.md + SESSION_STATUS refresh per Repo Hygiene §2 should land in
the next session that touches README so all three surfaces re-sync at
the same time. (Skipped this session because the count was already
stale before this gap and updating README is a documentation-shaped
task that wants its own commit, not a parity-gap closure commit.)

Run `/rom-parity-audit <next-file>.c` to start the next file audit, or
pick from `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` directly.
