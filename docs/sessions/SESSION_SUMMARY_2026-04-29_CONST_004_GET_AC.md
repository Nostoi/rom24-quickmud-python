# Session Summary — 2026-04-29 — `const.c` CONST-004 (GET_AC dex_app + IS_AWAKE gate)

## Scope

Closed the third and heaviest gap in the combat-math triplet —
`CONST-004`. Ports the ROM `dex_app[26]` table, adds a `get_ac(ch, type)`
accessor with the `IS_AWAKE` gate (position > SLEEPING), and rewires the
three ROM consumers: combat AC, `do_score` AC display, and the wiz
"stat char" AC line. With this, `mud/math/stat_apps.py` now mirrors the
full `merc.h:2104-2110` macro family.

## Outcomes

### `CONST-004` — ✅ FIXED

- **Python**: `mud/math/stat_apps.py::DEX_APP` + `get_ac`, `mud/combat/engine.py:391`, `mud/commands/session.py:160-176`, `mud/commands/imm_search.py:976-984`
- **ROM C**: `src/merc.h:2104-2106` (macro) + `src/const.c:821-848` (table); consumed at `src/fight.c:480-489`, `src/act_info.c:1591-1650`, `src/act_wiz.c:1612-1613`
- **Gap**: `CONST-004` — Combat AC and AC displays read raw `armor[ac_idx]` without `dex_app[get_curr_stat(STAT_DEX)].defensive` and without the ROM `IS_AWAKE` gate. DEX-3 missed +40 AC penalty; DEX-25 missed −120 AC bonus on every hit-roll and every score/stat display.
- **Fix**:
  - New `DEX_APP[26]` (single-column `defensive`) verbatim port of `src/const.c:821-848` in `mud/math/stat_apps.py`.
  - New `get_ac(ch, ac_type) -> int` accessor implements `armor[type] + (IS_AWAKE ? dex_app[DEX].defensive : 0)`. `_is_awake(ch)` mirrors `merc.h:2103` exactly (`position > 4`, i.e. > POS_SLEEPING).
  - Refactored: extracted shared `_curr_stat(ch, stat, default=13)` helper; existing `_curr_str` and new `_curr_dex` now both delegate to it.
  - Combat: `mud/combat/engine.py:391` (`attack_round` victim_ac) — swapped raw `victim.armor[ac_idx]` read to `get_ac(victim, ac_idx)`.
  - `do_score`: `mud/commands/session.py:160-176` — both the level-25+ numeric `Armor: pierce: ... bash: ... slash: ... magic: ...` line and the low-level tier description (`_armor_class_description(ac_slash)`) now read through `get_ac`.
  - Wiz "stat char": `mud/commands/imm_search.py` — the four-line AC display now reads through `get_ac` (matching ROM `src/act_wiz.c:1612-1613`).
- **Tests**: 11 new cases in `tests/integration/test_combat_dex_app.py` — table verification (5 parametrized DEX values), IS_AWAKE-off bypass (4 positions: SLEEPING / STUNNED / INCAP / DEAD), IS_AWAKE-on coverage (RESTING / SITTING / FIGHTING / STANDING), and an engine integration spy that asserts `attack_round` invokes `get_ac` and the DEX-25 standing victim's AC equals raw + (-120). All green.

## Files Modified

- `mud/math/stat_apps.py` — added `DexAppRow`, `DEX_APP[26]`, `_curr_stat`, `_curr_dex`, `_is_awake`, and `get_ac(ch, ac_type)`. Refactored `_curr_str` to delegate to `_curr_stat`.
- `mud/combat/engine.py` — imports `get_ac`; replaces raw `victim.armor[ac_idx]` read at L391.
- `mud/commands/session.py` — `do_score` AC reads route through `get_ac` (high-level numeric + low-level tier).
- `mud/commands/imm_search.py` — wiz "stat char" AC reads route through `get_ac`.
- `tests/integration/test_combat_dex_app.py` — new file, 11 cases.
- `docs/parity/CONST_C_AUDIT.md` — flipped `CONST-004` row → ✅ FIXED; flipped Phase 1 inventory row for `dex_app[26]` from ❌ MISSING → ✅ AUDITED.
- `CHANGELOG.md` — added `### Fixed` `CONST-004` entry under `[Unreleased]`.
- `pyproject.toml` — 2.6.49 → 2.6.50 (patch bump).

## Test Status

- `pytest tests/integration/test_combat_dex_app.py` — 11 / 11 passing.
- `pytest tests/integration/ tests/test_combat_thac0.py tests/test_combat_thac0_engine.py tests/test_combat_death.py tests/test_weapon_damage.py tests/test_player_combat_attributes.py tests/test_combat_defenses_prob.py tests/test_skill_combat_rom_parity.py` — 1569 passed / 10 skipped (no regressions).
- `ruff check mud/math/stat_apps.py tests/integration/test_combat_dex_app.py` — clean. Pre-existing ruff errors elsewhere in `mud/commands/session.py`, `mud/commands/imm_search.py`, `mud/combat/engine.py` are unchanged and out of scope.

## Next Steps

Combat-math triplet (CONST-002 / CONST-003 / CONST-004) is now **complete**. Remaining `const.c` gaps:

1. **`CONST-005`** (CRITICAL) — `advance_level` per-level HP gain currently uses the static `LEVEL_BONUS[ch_class]` dict in `mud/advancement.py:91`. ROM `src/update.c:74-79` rolls `number_range(class_table.hp_min, class_table.hp_max) + con_app[CON].hitp`. Both the RNG roll and the CON modifier are absent. Pre-flight: confirm `class_table.hp_min` / `hp_max` are present on `mud/models/classes.py:ClassType` (audit comment suggested they may not be). If absent, port them from `src/const.c:394-419` first. Then port `con_app[26]` (single column `hitp`; the `shock` column is dead data per audit) into `mud/math/stat_apps.py` as `CON_APP`. The integration test must seed `rng_mm.seed_mm(<seed>)` inside the test (after the autouse fixture) and assert exact HP gain at high vs low CON.
2. **`CONST-006`** (IMPORTANT) — `wis_app[WIS].practice` add-on in `advance_level`. Pairs with CONST-005 — same function, single-column `wis_app` table from `src/const.c:790-817`.

After CONST-005 + CONST-006 close, flip `const.c` row in `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` from ⚠️ Partial 80% → ✅ Audited (CONST-001 stays parked for NANNY-009; CONST-007 stays parked for OLC).

Continuing this session with `/rom-gap-closer CONST-005`.
