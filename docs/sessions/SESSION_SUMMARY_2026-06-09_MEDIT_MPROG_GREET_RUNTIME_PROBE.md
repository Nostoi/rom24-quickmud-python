# Session Summary — 2026-06-09 — MEdit greet mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from the previous MEdit
`TRIG_ENTRY` runtime probe. This session read the ROM movement and mobprog
dispatch path for PC room entry, then added coverage for the sibling
OLC-created `greet` mobprog path without changing production runtime behavior.

## Outcomes

### MEdit-created `TRIG_GREET` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/act_move.c:243`,
  `src/mob_prog.c:1325-1345`
- **Gap**: none found. The existing implementation already carries the
  builder-created `MobProgram` and `TRIG_GREET` bit into spawned NPC instances,
  and PC directional movement reaches `mp_greet_trigger`.
- **Coverage**: added
  `test_addmprog_created_greet_trigger_fires_for_entering_pc`, which runs
  `_interpret_medit("addmprog ... greet 100")`, spawns the edited mob
  prototype, moves a PC north into the mob's room, and verifies the runtime
  `mp_greet_trigger` path selects `Trigger.GREET` with the entering PC as actor.

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added the MEdit →
  spawn → PC movement → greet trigger probe.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion.
- `CHANGELOG.md` — added `2.13.44` entry for the new dynamic coverage.
- `pyproject.toml` — `2.13.43` → `2.13.44`.

## Test Status

- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_greet_trigger_fires_for_entering_pc`
  — 1 passed.
- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py tests/test_movement_mobprog.py tests/test_mobprog_triggers.py tests/integration/test_mobprog_greet_trigger.py`
  — 44 passed.
- `ruff check .` — clean.
- `PYTHONPATH=. pytest -q` — 5468 passed, 5 skipped.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are another OLC-created mobprog
runtime trigger path (`speech` or `act`) with primary ROM source read first, or
a non-combat lifecycle probe outside mobprogs. Avoid RNG-locked combat until
seed alignment has its own grounded probe.
