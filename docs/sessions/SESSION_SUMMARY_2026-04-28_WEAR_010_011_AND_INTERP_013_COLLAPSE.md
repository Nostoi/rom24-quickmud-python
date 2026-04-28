# Session Summary — 2026-04-28 — `act_obj.c` WEAR-010/011 + `interp.c` INTERP-013 collapse

## Scope

Cross-file follow-up from the prior `interp.c` session. `INTERP-013`
(`wield`/`hold` should dispatch to `do_wear` per ROM `cmd_table`)
was blocked because Python's `do_wear` didn't subsume the WIELD and
HOLD branches. This session opened two new gaps in `ACT_OBJ_C_AUDIT.md`,
closed them, then collapsed `INTERP-013`.

Note on gap IDs: the prior session's handoff used `WEAR-001`/`WEAR-002`
as placeholder IDs without realizing they collide with already-closed
gaps. Per audit-doc methodology (IDs are stable forever, never
renumber), the new gaps were filed as `WEAR-010`/`WEAR-011`.

## Outcomes

### `WEAR-010` — ✅ FIXED

- **Python**: `mud/commands/equipment.py:158-163` (`do_wear` weapon
  dispatch), `:282-388` (`_dispatch_wield` extracted helper).
- **ROM C**: `src/act_obj.c:1401-1697` (`wear_obj` single dispatcher).
- **Gap**: ROM `cmd_table` maps `wear`, `wield`, `hold` all to
  `do_wear` (`src/interp.c:103, 215, 232`). `do_wear` calls `wear_obj`
  which dispatches via `CAN_WEAR(obj, ITEM_X)` — so a weapon wears via
  the WIELD branch. Python `do_wear` instead returned
  `"You need to wield weapons, not wear them."` User-visible
  divergence: `wear sword` succeeds in ROM, failed in Python.
- **Fix**: Extracted `_dispatch_wield(ch, obj)` from `do_wield`
  (slot-replace, STR check, alignment, two-hand/shield, equip,
  weapon-skill flavor). `do_wear` now routes `item_type == WEAPON`
  through it.
- **Tests**: `tests/integration/test_equipment_system.py::test_wear_010_do_wear_dispatches_weapon_to_wield`.
- **Commit**: `66a17f1`.

### `WEAR-011` — ✅ FIXED

- **Python**: `mud/commands/equipment.py:451-460`.
- **ROM C**: `src/act_obj.c:1670-1677` (HOLD branch of `wear_obj`).
- **Gap**: ROM HOLD branch calls `remove_obj(WEAR_HOLD, fReplace=TRUE)`
  which auto-unequips the existing held item. Python `do_hold`
  rejected with `"You're already holding {name}."` (Note: `do_wear`'s
  HOLD branch already auto-replaced correctly; only standalone
  `do_hold` diverged.)
- **Fix**: `do_hold` now calls `_unequip_to_inventory(existing)` —
  identical to what `do_wear`'s HOLD branch already did.
- **Tests**: `tests/integration/test_equipment_system.py::test_wear_011_do_hold_auto_replaces_existing_held`.
- **Commit**: `7aba8a5`.

### `INTERP-013` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:336` (single Command with
  aliases), `mud/commands/equipment.py:282-289, 383-390` (`do_wield`/
  `do_hold` collapsed to thin wrappers).
- **ROM C**: `src/interp.c:103, 215, 232` (cmd_table entries).
- **Gap**: Python had separate `do_wield`/`do_hold` Commands. ROM has
  one function with three names. With `WEAR-010`/`WEAR-011` closed,
  `do_wear` now correctly handles the full dispatcher matrix.
- **Fix**: `do_wield`/`do_hold` collapsed to `return do_wear(ch, args)`
  thin wrappers (preserving direct-import callers in tests/scripts).
  Dispatcher registers
  `Command("wear", do_wear, aliases=("wield", "hold"), min_position=Position.RESTING)`.
- **Tests**: `tests/integration/test_interp_dispatcher.py::test_interp_013_wear_wield_hold_share_do_wear`.
- **Side-effects** (intentional, ROM-faithful):
  - `wield ring` now wears the ring on a finger (was: "You can't wield that.")
  - `hold sword` now wields the sword (was: "You can't hold that.")
  - `wield`/`hold` with no arg now emit "Wear, wield, or hold what?"
    (was: "Wield what?" / "Hold what?")
- **Commit**: bundled with handoff (this session).

## Files Modified

- `mud/commands/equipment.py` — extracted `_dispatch_wield`; `do_wear`
  routes weapons through it; `do_hold` auto-replaces; `do_wield`/
  `do_hold` collapsed to wrappers.
- `mud/commands/dispatcher.py` — single `Command("wear", ...)` with
  aliases for `wield`/`hold`.
- `tests/integration/test_equipment_system.py` — added 2 tests
  (WEAR-010, WEAR-011).
- `tests/integration/test_interp_dispatcher.py` — added 1 test
  (INTERP-013).
- `docs/parity/ACT_OBJ_C_AUDIT.md` — added WEAR-010/011 rows (✅ FIXED).
- `docs/parity/INTERP_C_AUDIT.md` — flipped INTERP-013 → ✅ FIXED.
- `CHANGELOG.md` — added `[2.6.13]` section.
- `pyproject.toml` — `2.6.12` → `2.6.13`.

## Test Status

- `pytest tests/integration tests/test_alias_parity.py tests/test_help_system.py tests/test_communication.py`
  → **1233 passed, 10 skipped, 0 failed** (~4:35 wall-clock).
- New tests this iteration: 3 (WEAR-010, WEAR-011, INTERP-013).

## Audit Progress

- `interp.c`: **24 / 24 gaps fixed + 1 closed-deferred** — all
  closeable gaps closed. Tracker can flip to ✅ AUDITED.
- `act_obj.c`: WEAR-001..011 all closed. Tracker stays ✅ AUDITED
  (was already 100%).
- ROM C files audited overall: **16 / 43**.

## Next Steps

`interp.c` is fully closed. Pick the next P0/P1 file from
`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`. Outstanding cleanup
carried over:

- **RNG-isolation flake** between integration and unit suites
  (`tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`,
  `tests/integration/test_character_advancement.py::test_kill_mob_grants_xp_integration`)
  — same root cause: no session-scoped `rng_mm.seed_mm` autouse fixture
  in `tests/conftest.py`.
