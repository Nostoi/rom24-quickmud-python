# Session Summary — 2026-04-29 — `const.c` CONST-002 (GET_HITROLL str_app augmentation)

## Scope

Picked up from the `const.c` Phase 1–3 audit handoff (commit `66438a3`, 7 stable
gap IDs filed). Closed the first CRITICAL combat-math gap, `CONST-002` —
`GET_HITROLL` macro consumption in `mud/combat/engine.py`. Single TDD cycle,
single commit. Sets up the shared `str_app`/`dex_app` infrastructure the
remaining triplet (CONST-003, CONST-004) will reuse.

## Outcomes

### `CONST-002` — ✅ FIXED

- **Python**: `mud/math/stat_apps.py` (new), `mud/combat/engine.py:411,420`
- **ROM C**: `src/merc.h:2107-2108` (macro), `src/const.c:728-755` (table), consumed at `src/fight.c:471`
- **Gap**: `CONST-002` — Combat read raw `attacker.hitroll` without `str_app[get_curr_stat(STAT_STR)].tohit`. STR-3 attacker missed −3 to-hit; STR-25 attacker missed +6.
- **Fix**: New `mud/math/stat_apps.py` module ports the full ROM `str_app[26]` table verbatim (4 columns: tohit, todam, carry, wield) as `STR_APP: tuple[StrAppRow, ...]`. New `get_hitroll(ch) -> int` accessor implements `ch->hitroll + str_app[STR].tohit` faithfully, with a defensive fall-back to the neutral STR-13 row if the character has no `get_curr_stat` and no `perm_stat`. `mud/combat/engine.py` now calls `get_hitroll(attacker)` at both attack paths — the THAC0 path at L411 (when `COMBAT_USE_THAC0=True`) and the percent fallback at L420.
- **Tests**: 8 new cases in `tests/integration/test_combat_str_app.py` — table verification (5 parametrized STR values), raw-hitroll preservation, THAC0 path engine integration (monkeypatches `COMBAT_USE_THAC0` on, spies `compute_thac0`), percent path engine integration (spies `engine.get_hitroll`). All green.

The `STR_APP` table also satisfies the prerequisite for `CONST-003` (todam column already in place; only the accessor + one engine swap remain).

## Files Modified

- `mud/math/stat_apps.py` — new module: `STR_APP` table + `get_hitroll(ch)`.
- `mud/combat/engine.py` — import `get_hitroll`; replace `attacker.hitroll` reads at L411 (THAC0 kwarg) and L420 (percent fallback) with `get_hitroll(attacker)`. ROM citations added on both lines.
- `tests/integration/test_combat_str_app.py` — new file, 8 cases.
- `docs/parity/CONST_C_AUDIT.md` — flipped `CONST-002` row → ✅ FIXED; flipped the Phase 2 `str_app` consumer table row for `merc.h:2107-2108` → ✅.
- `CHANGELOG.md` — added `### Fixed` `CONST-002` entry.
- `pyproject.toml` — 2.6.47 → 2.6.48 (patch bump per AGENTS.md Repo Hygiene §3).

## Test Status

- `pytest tests/integration/test_combat_str_app.py` — 8 / 8 passing.
- `pytest tests/integration/ tests/test_combat_thac0.py tests/test_combat_thac0_engine.py tests/test_combat_death.py` — 1424 passed / 10 skipped (no regressions).
- `pytest tests/ --ignore=tests/integration -q` — 197 passed, 1 pre-existing failure (`tests/test_area_loader.py::test_mob_flag_removal_lines_clear_flags`, confirmed pre-existing on `git stash` master).
- `ruff check mud/math/stat_apps.py tests/integration/test_combat_str_app.py` — clean. `mud/combat/engine.py` carries 12 pre-existing B009 warnings (`getattr` with constant attribute) on lines 1448/1450 and similar — out of scope for this gap.

## Next Steps

1. **`CONST-003`** (CRITICAL) — `GET_DAMROLL` adds `str_app[STR].todam`. Add `get_damroll(ch)` to `mud/math/stat_apps.py` (table is already imported), swap `attacker.damroll` at `mud/combat/engine.py:1184` (the `dam += attacker.damroll * min(100, skill) // 100` site — also fix the `//` to `c_div` per AGENTS.md Parity Rules; that's a separate combat-math note in the audit doc but lands cleanly with this swap). Test mirrors `test_combat_str_app.py` shape.
2. **`CONST-004`** (CRITICAL) — `GET_AC` adds `dex_app[DEX].defensive`. Needs new `DEX_APP[26]` table (single column) ported from `src/const.c:821-848`. Touches `mud/combat/engine.py:391` (combat AC) and the score/look display paths in `mud/commands/session.py` and `mud/commands/imm_search.py:986`. The `IS_AWAKE(ch)` gate from `merc.h:2104-2106` must be honored — sleeping/stunned chars don't get DEX defensive AC.
3. **`CONST-005`** (CRITICAL) — `advance_level` HP roll. Verify `class_table.hp_min/hp_max` are present on `mud/models/classes.py:ClassType` before porting. Port `con_app[26]` table (hitp column only — `shock` is dead data per audit).
4. **`CONST-006`** (IMPORTANT) — `wis_app[WIS].practice` in `advance_level`. Pairs naturally with CONST-005.

After CONST-002..006 close, flip `const.c` row in `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` from ⚠️ Partial 80% → ✅ Audited (CONST-001 + CONST-007 stay deferred per their respective dedicated-session plans).

Run `/rom-gap-closer CONST-003` to continue.
