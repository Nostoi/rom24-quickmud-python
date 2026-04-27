# Session Summary — 2026-04-27 — act_obj.c reconciliation + mob_cmds.c audit (MOBCMD-014)

## Scope

Picked up after the do_drop / act_obj batch commits had landed without
formalizing gap IDs. Goal: stop the doc/code drift on `act_obj.c` and open
the next P1 audit. Three commits delivered.

## Outcomes

### `act_obj.c` — ✅ AUDITED (100%)

- **Audit doc**: `docs/parity/ACT_OBJ_C_AUDIT.md`
- **ROM C**: `src/act_obj.c` (full file, 1,661 lines verified)
- **Action**: Refresh sweep against current Python post-commits 97c901e
  (`finish do_drop parity batch`) and 517542b (`close get/put/drop/give/wear/
  sacrifice/recite/brandish/zap/steal gaps`). All 12 audited functions
  (`do_get`/`do_put`/`do_drop`/`do_give`/`do_remove`/`do_sacrifice`/`do_quaff`/
  `do_drink`/`do_eat`/`do_fill`/`do_pour`/`do_recite`/`do_brandish`/`do_zap`
  plus `do_wear`/`do_wield`/`do_hold` and `do_steal`) verified at 100% parity.
- **Tests**: `pytest tests/integration/ -k "drop or remove or sacrifice or drink or eat or quaff or fill or pour or recite or brandish or zap"` → 193 passed, 2 skipped (unrelated).
- **Verification**: TO_ROOM broadcasts present in `mud/commands/inventory.py:637-690`
  (do_drop coin + obj + MELT_DROP smoke); no `random.*` drift in
  consumption/magic_items/liquids; IntEnum flag usage throughout.
- **Tracker**: `mob_cmds.c` row was unchanged; `act_obj.c` flipped from
  🔄 IN PROGRESS / ~60% to ✅ COMPLETE / 100%. P1 summary 5/11 (81%) → 6/11 (86%).

### `mob_cmds.c` — 🔄 IN PROGRESS (audit doc opened, 18 gap IDs)

- **Audit doc**: `docs/parity/MOB_CMDS_C_AUDIT.md` (new)
- **ROM C**: `src/mob_cmds.c` (1,369 lines)
- **Action**: Phase 1 (function inventory: 31 `do_mp_*` functions, 29 mapped
  to `mud/mob_cmds.py`, 2 admin/debug to `mud/commands/mobprog_tools.py`) and
  Phase 3 (gap identification: stable IDs `MOBCMD-001`..`MOBCMD-018` —
  6 CRITICAL, 9 IMPORTANT, 3 MINOR) complete. Phase 4 (closure) opened.
- **Highest-impact gaps**: MOBCMD-014 (`do_mpdamage` raw HP decrement),
  MOBCMD-005/006 (`do_mpoload` missing level param), MOBCMD-008/009/010
  (`do_mpflee` randomization, NO_MOB check, move_char path),
  MOBCMD-015/016 (`do_mpcall` missing obj1/obj2 args),
  MOBCMD-011/012 (`do_mpcast` string targets vs TAR_* enum).

### `MOBCMD-014` — ✅ FIXED

- **Python**: `mud/mob_cmds.py:1088` (`do_mpdamage`)
- **ROM C**: `src/mob_cmds.c:1132-1145`
- **Gap**: ROM calls `damage(victim, victim, amount, TYPE_UNDEFINED, DAM_NONE,
  FALSE)`; Python had been raw-decrementing `victim.hit` with `max(0, ...)`,
  bypassing the death/position pipeline (no `update_pos`, no
  `mp_death_trigger`, no `raw_kill`, no corpse).
- **Fix**: `do_mpdamage` now routes through
  `mud.combat.engine.apply_damage(victim, victim, amount, dam_type=None,
  dt=None, show=False)`. `dam_type=None` bypasses Python's RIV class block
  since ROM's `DAM_NONE` has no class; `dt=None` mirrors `TYPE_UNDEFINED`;
  `show=False` matches ROM's `FALSE` (no broadcast).
- **Tests**: `tests/integration/test_mob_cmds_damage.py` — 2 new tests
  (`test_lethal_kill_runs_damage_pipeline`, `test_safe_form_caps_at_current_hit`).
  Verified failing pre-fix (`victim.position` stayed STANDING), passing
  post-fix.

## Files Modified

- `mud/mob_cmds.py` — `do_mpdamage` rewritten to route through
  `apply_damage`.
- `tests/integration/test_mob_cmds_damage.py` — new file, 2 tests covering
  lethal-kill pipeline and safe-form HP cap.
- `docs/parity/ACT_OBJ_C_AUDIT.md` — header flipped to ✅ 100% COMPLETE;
  appended "Final Audit Refresh (2026-04-27)" section with per-function
  verification matrix and evidence.
- `docs/parity/MOB_CMDS_C_AUDIT.md` — new audit doc; MOBCMD-014 row flipped
  to ✅ FIXED with commit reference.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `act_obj.c` row flipped
  to ✅ COMPLETE / 100%; `mob_cmds.c` row updated to point at new audit doc;
  P1 summary 5/11 → 6/11 (81% → 86%); total 13 → 14 audited.
- `CHANGELOG.md` — `[Unreleased]` Fixed entry for MOBCMD-014; Changed entry
  for the act_obj.c reconciliation.

## Test Status

- `pytest tests/integration/test_mob_cmds_damage.py tests/integration/test_mobprog_*.py tests/integration/test_mob_ai.py tests/test_combat_death.py tests/test_combat.py` → 83 passed, 1 skipped (combat + mobprog suite).
- `pytest tests/integration/ -k "drop or remove or sacrifice or drink or eat or quaff or fill or pour or recite or brandish or zap"` → 193 passed, 2 skipped (act_obj-area regression check).
- Full suite `pytest tests/` → 3506 passed, 11 skipped, **2 pre-existing failures** (`tests/test_game_loop.py::test_mobile_update_returns_home_when_out_of_zone` and `tests/test_mobprog_triggers.py::test_event_hooks_fire_rom_triggers`). Both also fail on `HEAD~1`; unrelated to this session.
- `ruff check mud/mob_cmds.py tests/integration/test_mob_cmds_damage.py` → 1 pre-existing `B010` warning at `mud/mob_cmds.py:1034` (unrelated to this session's edits).

## Next Steps

Continue closing CRITICAL gaps on `mob_cmds.c` via `/rom-gap-closer`. Recommended order (one gap = one commit):

1. **MOBCMD-005** — `do_mpoload` missing level parameter (ROM signature is `(vnum, level, R|W mode)`).
2. **MOBCMD-010** — `do_mpflee` should call `move_char` not `_move_to_room` so move-points/AT_ROOM triggers fire.
3. **MOBCMD-008** — `do_mpflee` 6-iteration `random_door()` randomization.
4. **MOBCMD-015** — `do_mpcall` missing obj1/obj2 args.
5. **MOBCMD-011** — `do_mpcast` enum-based TAR_* dispatch.
6. **MOBCMD-003** — `do_mpkill` POS_FIGHTING gating.

When all 6 CRITICAL + 9 IMPORTANT close: bump `pyproject.toml` patch
version, flip the `mob_cmds.c` tracker row to ✅, and write the closing
session summary.
