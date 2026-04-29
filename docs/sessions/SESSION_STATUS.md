# Session Status — 2026-04-29 — `const.c` CONST-002 Closed (combat-math triplet 1/3)

## Current State

- **Active audit**: `const.c` (Phase 4 — per-gap closures in flight).
- **Last completed**: `CONST-002` (`GET_HITROLL` adds `str_app[STR].tohit`; new `mud/math/stat_apps.py` module with full `STR_APP[26]` table; both engine attack paths route through `get_hitroll(attacker)`). Commit `16a4c4b`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-29_CONST_002_GET_HITROLL.md](SESSION_SUMMARY_2026-04-29_CONST_002_GET_HITROLL.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.48 |
| Tests | 1424 passing / 10 skipped (full integration suite + combat units; 1 pre-existing unit-suite failure in `test_area_loader.py` unrelated to combat). |
| ROM C files audited | 18 / 43 (42%) ✅ Audited; `const.c` ⚠️ Partial 80% (3 CRITICAL + 2 IMPORTANT + 1 MINOR open: CONST-003, CONST-004, CONST-005, CONST-006, CONST-001 deferred to NANNY-009, CONST-007 deferred to OLC). |
| Active focus | `const.c` — combat-math triplet, 1/3 closed. |

## Next Intended Task

**`CONST-003`** (CRITICAL) — `GET_DAMROLL` adds `str_app[STR].todam`. The `STR_APP` table is already imported in `mud/math/stat_apps.py`, so the close is small: add `get_damroll(ch) -> int` accessor, swap `attacker.damroll` at `mud/combat/engine.py:1184`. While there, also convert the adjacent `attacker.damroll * min(100, skill) // 100` to use `c_div` per AGENTS.md ROM Parity Rules (the audit doc flags this `//` separately but it lives one line away from the `damroll` read).

Test should mirror `tests/integration/test_combat_str_app.py` shape — parametrized STR values with expected `todam`, raw-damroll preservation, and at least one engine-level integration that exercises the `calculate_weapon_damage` path with two STR extremes and asserts the damage delta matches `STR_APP[hi].todam - STR_APP[lo].todam`.

After CONST-003: `CONST-004` (`GET_AC` + new `DEX_APP[26]` table, `IS_AWAKE` gate, score/look display sites in `mud/commands/session.py:208` and `mud/commands/imm_search.py:986`), then `CONST-005` (advance_level HP roll + `con_app`), then `CONST-006` (wis_app practice). `CONST-001` stays parked for NANNY-009; `CONST-007` stays parked for the OLC audit.

Run `/rom-gap-closer CONST-003` to continue.
