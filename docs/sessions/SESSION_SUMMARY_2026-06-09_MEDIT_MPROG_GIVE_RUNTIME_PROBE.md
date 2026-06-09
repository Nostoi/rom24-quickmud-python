# Session Summary — 2026-06-09 — MEdit give mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from the MEdit `TRIG_ENTRY`,
`TRIG_GREET`, `TRIG_SPEECH`, `TRIG_ACT`, and `TRIG_BRIBE` runtime probes. This
session read the ROM `do_give` / `mp_give_trigger` path and added coverage for
an OLC-created `give` mobprog reaching the player-facing object-give runtime
dispatch path without changing production behavior.

## Outcomes

### MEdit-created `TRIG_GIVE` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/act_obj.c:849-850`,
  `src/mob_prog.c:1283-1323`
- **Gap**: none found. The existing implementation already carries the
  builder-created `MobProgram` and `TRIG_GIVE` bit into spawned NPC instances,
  and the object `do_give` path reaches give-trigger selection with the given
  object as ROM's `arg1`.
- **Coverage**: added
  `test_addmprog_created_give_trigger_fires_when_pc_gives_object`, which runs
  `_interpret_medit("addmprog ... give relic")`, spawns the edited mob
  prototype, runs `do_give()` from a PC giving a carried object in the same
  room, and verifies the runtime give trigger selects the OLC-created program
  with the PC actor and object argument.

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added the MEdit →
  spawn → object `do_give` → give-trigger probe.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion.
- `CHANGELOG.md` — added `2.13.48` entry for the new dynamic coverage.
- `pyproject.toml` — `2.13.47` → `2.13.48`.
- `docs/sessions/SESSION_STATUS.md` — refreshed the current pointer.

## Test Status

- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_give_trigger_fires_when_pc_gives_object`
  — 1 passed.
- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_inv025_communication_act_trigger_dispatch.py tests/integration/test_npc_speaker_does_not_trigger_speech.py tests/integration/test_give_command.py tests/integration/test_mobprog_give_trigger.py tests/integration/test_inv025_do_give_act_trigger_suppression.py`
  — 64 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.
- `PYTHONPATH=. pytest -q` — 5472 passed, 5 skipped.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are another OLC-created mobprog
trigger family that can be driven without RNG, or a non-combat lifecycle probe
that already has a clear ROM source path. Avoid RNG-locked combat until seed
alignment has its own grounded probe.
