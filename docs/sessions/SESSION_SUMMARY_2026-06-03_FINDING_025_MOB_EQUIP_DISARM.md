# Session Summary — 2026-06-03 — FINDING-025 mob equip/disarm (2.13.8)

## Scope

Picked up from `SESSION_SUMMARY_2026-06-03_FINDING_024_SAVE_LOAD_CARRY_SEQ.md`.
The active mode remains the cross-file invariants / divergence-class sweep.
This session closed **FINDING-025**, the mob-equipment leg of class-13 object
ordering/equipment representation work.

## Outcome

### FINDING-025 — mob equipment lookup + disarm reclaim — ✅ RESOLVED

- **Python**: `mud/combat/engine.py:get_wielded_weapon`,
  `mud/spawning/templates.py:MobInstance.remove_object`,
  `mud/skills/handlers.py:disarm`
- **ROM C**: `src/handler.c:get_eq_char` scans `ch->carrying` for
  `obj->wear_loc == iWear`; `src/fight.c:disarm` drops the weapon to the room,
  then lets an NPC victim with `wait == 0` immediately `get_obj` it back when
  visible.
- **Probe result**: `MobInstance.equip`'s inventory+`wear_loc` representation is
  ROM-faithful, not a divergence by itself. The real gap was shared consumers:
  `get_wielded_weapon` only checked `wielded_weapon` and PC `equipment` dict
  entries, so reset-equipped mobs could look unarmed.
- **Fix**: `get_wielded_weapon` now falls back to scanning `inventory` for
  `wear_loc == WearLocation.WIELD`; `MobInstance.remove_object` clears
  `carried_by` and `wear_loc`; `disarm` mirrors ROM's NODROP/INVENTORY
  carry-list branch and NPC immediate visible-weapon reclaim branch.
- **Regression**: `tests/integration/test_finding025_mob_equip_disarm.py` covers
  mob `wear_loc` lookup, NPC disarm auto-reclaim, and the mob NODROP branch. The
  stale assertion in `tests/test_skill_combat_rom_parity.py::TestDisarmRomParity::
  test_disarm_success_drops_weapon_to_room` was corrected to the ROM NPC
  reclaim behavior.

## Files Modified

- `mud/combat/engine.py`
- `mud/skills/handlers.py`
- `mud/spawning/templates.py`
- `tests/integration/test_finding025_mob_equip_disarm.py`
- `tests/test_skill_combat_rom_parity.py`
- `tools/diff_harness/FINDINGS.md`
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
- `CHANGELOG.md`
- `pyproject.toml`

## Test Status

- Focused + disarm slice:
  `pytest -n0 tests/integration/test_finding025_mob_equip_disarm.py tests/test_skill_combat_rom_parity.py::TestDisarmRomParity -q`
  → 17 passed
- Adjacent regression/convention slice:
  `pytest -n0 tests/integration/test_finding025_mob_equip_disarm.py tests/integration/test_fight038_disarm_noremove_improve.py tests/integration/test_fight_026_npc_offensive_skill_no_crash.py tests/test_equipment_key_convention.py tests/test_attribute_convention.py -q`
  → 9 passed
- `ruff check .` → clean
- `ruff format --check mud/combat/engine.py mud/skills/handlers.py mud/spawning/templates.py tests/integration/test_finding025_mob_equip_disarm.py tests/test_skill_combat_rom_parity.py`
  → clean

## Next Steps

1. Continue Phase C deterministic diff-harness widening: light hold and
   money/shop paths.
2. Add RNG-locked combat scenarios only after seed alignment is proven.
