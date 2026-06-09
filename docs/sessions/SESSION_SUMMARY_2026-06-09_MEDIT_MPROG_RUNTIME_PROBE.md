# Session Summary — 2026-06-09 — MEdit mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from
`SESSION_SUMMARY_2026-06-09_TABLES004_MEDIT_MPROG_FLAGS.md`. The prior session
fixed MEdit `addmprog` trigger flag values, so this session probed the next
runtime edge: whether an OLC-created `entry` mobprog on a `MobIndex` survives
`spawn_mob` and is selected by directional movement's ROM `TRIG_ENTRY` dispatch.

## Outcomes

### MEdit-created `TRIG_ENTRY` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/act_move.c:240-241`
- **Gap**: none found. The existing implementation already carries the
  builder-created `MobProgram` and `mprog_flags` into spawned NPC instances.
- **Coverage**: added `test_addmprog_created_entry_trigger_fires_after_spawn`,
  which runs `_interpret_medit("addmprog ... entry 100")`, spawns the edited
  mob prototype, moves the NPC north, and verifies the real
  `mp_percent_trigger` path selected the OLC-created program.

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added the runtime
  MEdit → spawn → movement probe.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion.
- `CHANGELOG.md` — added `2.13.43` entry for the new dynamic coverage.
- `pyproject.toml` — `2.13.42` → `2.13.43`.

## Test Status

- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_entry_trigger_fires_after_spawn` — 1 passed.
- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py tests/test_movement_mobprog.py tests/test_mobprog_triggers.py tests/integration/test_mobprog_greet_trigger.py` — 43 passed.
- `PYTHONPATH=. pytest -q` — 5467 passed, 5 skipped.
- `ruff check .` — clean.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are another OLC-created mobprog
runtime trigger path (`greet`, `speech`, or `act`) with primary ROM source read
first, or a non-combat lifecycle probe outside mobprogs. No production parity
gap is open from this session.
