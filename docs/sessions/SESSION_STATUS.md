# Session Status — 2026-06-03 — FINDING-025 mob equip/disarm (2.13.8)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **FINDING-025 — mob equip/disarm** ✅ RESOLVED (2.13.8).
    `MobInstance.equip`'s inventory+`wear_loc` model was verified as
    ROM-faithful; the real gap was shared consumers. `get_wielded_weapon` now
    scans carried objects by `wear_loc`, `MobInstance.remove_object` clears
    carrier/`wear_loc`, and `disarm` mirrors ROM's NODROP/INVENTORY carry-list
    branch plus the NPC immediate visible-weapon reclaim branch.
  - **FINDING-024 — save/load carry-list ordering** ✅ RESOLVED (2.13.7).
    `ObjectSave` persists `Object._carry_seq`, `_deserialize_object` restores it,
    and `from_orm` advances the runtime carry-sequence counter past restored
    values.
  - **FINDING-020 — equip→remove carry-list position** ✅ RESOLVED (PC path,
    2.13.6).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_FINDING_025_MOB_EQUIP_DISARM.md](SESSION_SUMMARY_2026-06-03_FINDING_025_MOB_EQUIP_DISARM.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.8 |
| Tests | Focused + disarm slice `pytest -n0 tests/integration/test_finding025_mob_equip_disarm.py tests/test_skill_combat_rom_parity.py::TestDisarmRomParity -q` → **17 passed**; adjacent slice `pytest -n0 tests/integration/test_finding025_mob_equip_disarm.py tests/integration/test_fight038_disarm_noremove_improve.py tests/integration/test_fight_026_npc_offensive_skill_no_crash.py tests/test_equipment_key_convention.py tests/test_attribute_convention.py -q` → **9 passed**; `ruff check .` clean |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Divergence class 13 | object-list ordering + equipment representation legs closed (INV-039 + FINDING-020 + FINDING-024 + FINDING-025) |
| Open engine findings | None currently called out in the latest session pointer |

## Next Intended Task

1. Continue Phase C deterministic diff-harness widening: light hold and
   money/shop paths.
2. Add RNG-locked combat scenarios only after seed alignment is proven.

## Other open / deferred items

- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.
