# Session Status — 2026-04-29 — `const.c` CONST-003 Closed (combat-math triplet 2/3)

## Current State

- **Active audit**: `const.c` (Phase 4 — per-gap closures in flight).
- **Last completed**: `CONST-003` (`GET_DAMROLL` adds `str_app[STR].todam`; `mud/math/stat_apps.py::get_damroll` + swap at `mud/combat/engine.py:1189`). Commit `b08d5c9`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-29_CONST_003_GET_DAMROLL.md](SESSION_SUMMARY_2026-04-29_CONST_003_GET_DAMROLL.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.49 |
| Tests | 1436 passing / 10 skipped (full integration + combat suite). 1 pre-existing unit-suite failure in `test_area_loader.py` unrelated to combat. |
| ROM C files audited | 18 / 43 (42%) ✅ Audited; `const.c` ⚠️ Partial 80% (2 CRITICAL + 2 IMPORTANT + 1 MINOR open: CONST-004, CONST-005, CONST-006, CONST-001 deferred to NANNY-009, CONST-007 deferred to OLC). |
| Active focus | `const.c` — combat-math triplet, 2/3 closed. |

## Next Intended Task

**`CONST-004`** (CRITICAL) — `GET_AC` adds `dex_app[DEX].defensive` with `IS_AWAKE` gate. This is the heaviest of the triplet:

1. Port `dex_app[26]` from `src/const.c:821-848` (single column `defensive`) into `mud/math/stat_apps.py` as `DEX_APP`.
2. Add `get_ac(ch, ac_type)` accessor mirroring `src/merc.h:2104-2106` — `ch->armor[ac_type] + (IS_AWAKE(ch) ? dex_app[DEX].defensive : 0)`. Sleeping/stunned victims do NOT get the DEX defensive.
3. Combat consumer: `mud/combat/engine.py:391` (currently reads `victim.armor[ac_idx]` raw) → swap to `get_ac(victim, ac_idx)`.
4. Display consumers: score path in `mud/commands/session.py:208`-area and imm "stat char" at `mud/commands/imm_search.py:986` — both read raw armor; ROM `act_info.c:1594-1645` runs them through `GET_AC` for the per-AC tier display strings. Confirm by re-reading both Python sites against the ROM display strings.
5. Test: parametrized DEX values matching `dex_app[26]`, an `IS_AWAKE`-off case (sleeping victim's AC equals raw armor), an engine-level integration varying victim DEX with pinned RNG.

After CONST-004: `CONST-005` (advance_level HP roll + `con_app[CON].hitp`; verify `class_table.hp_min/hp_max` are present on `mud/models/classes.py:ClassType` first), then `CONST-006` (`wis_app[WIS].practice` in `advance_level`). `CONST-001` parked for NANNY-009; `CONST-007` parked for OLC audit.

Run `/rom-gap-closer CONST-004` to continue.
