# Session Summary — 2026-04-29 — `const.c` CONST-003 (GET_DAMROLL str_app augmentation)

## Scope

Continued the `const.c` combat-math triplet. Closed `CONST-003` —
`GET_DAMROLL` macro consumption in `mud/combat/engine.py:1189`
(`calculate_weapon_damage`). Reused the `STR_APP[26]` table that landed
with CONST-002 in the previous session-summary — only the accessor and
the engine swap were new.

## Outcomes

### `CONST-003` — ✅ FIXED

- **Python**: `mud/math/stat_apps.py::get_damroll`, `mud/combat/engine.py:1189`
- **ROM C**: `src/merc.h:2109-2110` (macro), consumed at `src/fight.c:588` for the weapon-damage formula
- **Gap**: `CONST-003` — Combat read raw `attacker.damroll` without `str_app[get_curr_stat(STAT_STR)].todam`. STR-3 attacker missed −1 damage per swing; STR-25 attacker missed +9 damage per swing.
- **Fix**: New `get_damroll(ch) -> int` accessor in `mud/math/stat_apps.py` mirrors the macro: `ch.damroll + STR_APP[STR].todam`, with the same neutral-STR-13 fallback as `get_hitroll`. `calculate_weapon_damage` at `mud/combat/engine.py:1189` (the `dam += GET_DAMROLL(ch) * UMIN(100, skill) / 100` line) now routes through `get_damroll(attacker)`.
- **Tests**: 7 new cases in `tests/integration/test_combat_str_app.py` — table verification (5 parametrized STR values), raw-damroll preservation, engine-level integration via `calculate_weapon_damage` with pinned RNG (asserts the damage delta between STR-3 and STR-25 equals `STR_APP[25].todam - STR_APP[3].todam = 10`). All green. Existing `tests/test_weapon_damage.py` stays green because `create_test_character` leaves `perm_stat` empty, so the fallback returns the STR-13 neutral row (`todam=0`).

The `//` vs `c_div` issue on the same line at `mud/combat/engine.py:1189` is a separate combat-math gap per the audit doc and was deliberately left out of this commit per "one gap = one commit" discipline.

## Files Modified

- `mud/math/stat_apps.py` — added `get_damroll(ch)` alongside the existing `get_hitroll`.
- `mud/combat/engine.py` — imports `get_damroll`; replaces `attacker.damroll` at L1189 with `get_damroll(attacker)`.
- `tests/integration/test_combat_str_app.py` — extended `_make_attacker` to take a `damroll` kwarg; added 7 cases under a CONST-003 banner comment.
- `docs/parity/CONST_C_AUDIT.md` — flipped `CONST-003` row → ✅ FIXED; flipped Phase 2 `str_app` consumer table row for `merc.h:2109-2110` → ✅.
- `CHANGELOG.md` — added `### Fixed` `CONST-003` entry under `[Unreleased]`.
- `pyproject.toml` — 2.6.48 → 2.6.49 (patch bump).

## Test Status

- `pytest tests/integration/test_combat_str_app.py tests/test_weapon_damage.py` — 20 / 20 passing.
- `pytest tests/integration/ tests/test_combat_thac0.py tests/test_combat_thac0_engine.py tests/test_combat_death.py tests/test_weapon_damage.py` — 1436 passed / 10 skipped (no regressions).
- `ruff check mud/math/stat_apps.py tests/integration/test_combat_str_app.py` — clean. `mud/combat/engine.py` carries the same 12 pre-existing B009 warnings (unrelated, far from edit sites).

## Next Steps

1. **`CONST-004`** (CRITICAL) — `GET_AC` adds `dex_app[DEX].defensive`. This is the bigger gap of the triplet:
   - Port `dex_app[26]` table from `src/const.c:821-848` (single column `defensive`) into `mud/math/stat_apps.py` as `DEX_APP`.
   - Add `get_ac(ch, ac_type)` accessor mirroring `src/merc.h:2104-2106`: `ch->armor[ac_type] + (IS_AWAKE(ch) ? dex_app[DEX].defensive : 0)`. The `IS_AWAKE` gate (Position > SLEEPING) must be honored.
   - Combat consumer: `mud/combat/engine.py:391` — currently reads `victim.armor[ac_idx]` raw. Swap to `get_ac(victim, ac_idx)`.
   - Display consumers: `mud/commands/session.py:208`-area (score) and `mud/commands/imm_search.py:986` ("stat char" display) read raw armor values too — ROM `act_info.c:1594-1645` runs them through `GET_AC` for the per-AC tier display strings.
   - Test pattern: parametrized DEX values matching `dex_app[26]`, an `IS_AWAKE`-off case (sleeping victim's AC equals raw armor), and an engine-level integration that varies victim DEX while pinning RNG and asserts attack hit-rate matches the AC delta.

2. **`CONST-005`** (CRITICAL) — `advance_level` HP roll. Verify `class_table.hp_min`/`hp_max` exist on `mud/models/classes.py:ClassType` first; port `con_app[26]` (hitp column only).

3. **`CONST-006`** (IMPORTANT) — `wis_app[WIS].practice` in `advance_level`. Pairs with CONST-005.

After CONST-002..006 close, flip `const.c` row in `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` from ⚠️ Partial 80% → ✅ Audited (CONST-001 deferred to NANNY-009; CONST-007 deferred to OLC).

Continuing this session with `/rom-gap-closer CONST-004`.
