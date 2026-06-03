# Handoff — 2026-06-03 — FINDING-025 mob equip/disarm

## Current State

FINDING-025 is implemented and verified locally, but the changes are still
uncommitted in the worktree. `docs/sessions/SESSION_STATUS.md` now points at
`SESSION_SUMMARY_2026-06-03_FINDING_025_MOB_EQUIP_DISARM.md`, and
`pyproject.toml` is bumped to `2.13.8`.

## What Landed

- `mud/combat/engine.py:get_wielded_weapon` now falls back to scanning
  `inventory` for `wear_loc == WearLocation.WIELD`, matching ROM
  `src/handler.c:get_eq_char`.
- `mud/spawning/templates.py:MobInstance.remove_object` now clears
  `carried_by` and `wear_loc`, matching ROM `obj_from_char`.
- `mud/skills/handlers.py:disarm` now mirrors ROM `src/fight.c:2257-2265` for
  both NODROP/INVENTORY carry-list re-add and NPC immediate visible-weapon
  reclaim.
- `tests/integration/test_finding025_mob_equip_disarm.py` covers:
  mob inventory+`wear_loc` wield lookup, normal NPC disarm auto-reclaim, and mob
  NODROP disarm re-add.
- `tests/test_skill_combat_rom_parity.py::TestDisarmRomParity::
  test_disarm_success_drops_weapon_to_room` was corrected to ROM's NPC reclaim
  behavior.
- Durable docs updated: `tools/diff_harness/FINDINGS.md`,
  `docs/parity/DIVERGENCE_CLASS_ROSTER.md`, `CHANGELOG.md`,
  `docs/sessions/SESSION_SUMMARY_2026-06-03_FINDING_025_MOB_EQUIP_DISARM.md`,
  and `docs/sessions/SESSION_STATUS.md`.

## Verification Run

- `pytest -n0 tests/integration/test_finding025_mob_equip_disarm.py tests/test_skill_combat_rom_parity.py::TestDisarmRomParity -q`
  → 17 passed
- `pytest -n0 tests/integration/test_finding025_mob_equip_disarm.py tests/integration/test_fight038_disarm_noremove_improve.py tests/integration/test_fight_026_npc_offensive_skill_no_crash.py tests/test_equipment_key_convention.py tests/test_attribute_convention.py -q`
  → 9 passed
- `ruff check .` → clean
- `ruff format --check mud/combat/engine.py mud/skills/handlers.py mud/spawning/templates.py tests/integration/test_finding025_mob_equip_disarm.py tests/test_skill_combat_rom_parity.py`
  → clean
- `git diff --check` → clean

GitNexus MCP tools were not exposed in this Codex harness (`tool_search` found
none), so impact/detect-change work used the documented fallback: ROM source
reads, local reference search, and targeted regression slices.

## Worktree At Handoff

Expected modified/untracked files:

- `CHANGELOG.md`
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
- `docs/sessions/SESSION_STATUS.md`
- `docs/sessions/SESSION_SUMMARY_2026-06-03_FINDING_025_MOB_EQUIP_DISARM.md`
- `docs/sessions/HANDOFF_2026-06-03_FINDING_025_MOB_EQUIP_DISARM.md`
- `mud/combat/engine.py`
- `mud/skills/handlers.py`
- `mud/spawning/templates.py`
- `pyproject.toml`
- `tests/integration/test_finding025_mob_equip_disarm.py`
- `tests/test_skill_combat_rom_parity.py`
- `tools/diff_harness/FINDINGS.md`

## Next Intended Task

Continue Phase C deterministic diff-harness widening: light hold and money/shop
paths. Add RNG-locked combat scenarios only after seed alignment is proven.

## Deferred / Known Issues

- `test-fixtures-lint` remains manual-staged until legacy tests migrate.
- `test_all_commands.py` still has the pre-existing `exits` attribute error.
