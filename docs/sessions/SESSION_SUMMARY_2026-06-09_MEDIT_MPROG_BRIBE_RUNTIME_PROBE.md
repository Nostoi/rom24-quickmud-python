# Session Summary — 2026-06-09 — MEdit bribe mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from the MEdit `TRIG_ENTRY`,
`TRIG_GREET`, `TRIG_SPEECH`, and `TRIG_ACT` runtime probes. This session read
the ROM `do_give` / `mp_bribe_trigger` path and added coverage for an
OLC-created `bribe` mobprog reaching the player-facing runtime dispatch path
without changing production behavior.

## Outcomes

### MEdit-created `TRIG_BRIBE` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/act_obj.c:734-735`,
  `src/mob_prog.c:1224-1242`
- **Gap**: none found. The existing implementation already carries the
  builder-created `MobProgram` and `TRIG_BRIBE` bit into spawned NPC instances,
  and the money `do_give` path reaches bribe-trigger selection with ROM's
  threshold comparison.
- **Coverage**: added
  `test_addmprog_created_bribe_trigger_fires_when_pc_gives_coins`, which runs
  `_interpret_medit("addmprog ... bribe 20")`, spawns the edited mob prototype,
  runs `do_give()` from a PC giving 20 silver in the same room, and verifies the
  runtime bribe trigger selects the OLC-created program with the PC as actor.

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added the MEdit →
  spawn → money `do_give` → bribe-trigger probe.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion.
- `CHANGELOG.md` — added `2.13.47` entry for the new dynamic coverage.
- `pyproject.toml` — `2.13.46` → `2.13.47`.
- `docs/sessions/SESSION_STATUS.md` — refreshed the current pointer.

## Test Status

- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_bribe_trigger_fires_when_pc_gives_coins`
  — 1 passed.
- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_bribe_trigger_fires_when_pc_gives_coins tests/integration/test_give_command.py::test_give_gold_to_npc_fires_bribe_trigger_with_gold_scaled_to_copper`
  — 2 passed.
- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_inv025_communication_act_trigger_dispatch.py tests/integration/test_npc_speaker_does_not_trigger_speech.py tests/integration/test_give_command.py`
  — 60 passed.
- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_inv025_communication_act_trigger_dispatch.py tests/integration/test_npc_speaker_does_not_trigger_speech.py tests/integration/test_give_command.py`
  — 60 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.
- `PYTHONPATH=. pytest -q` — 5471 passed, 5 skipped.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are another OLC-created mobprog
trigger family that can be driven without RNG, or a non-combat lifecycle probe
that already has a clear ROM source path. Avoid RNG-locked combat until seed
alignment has its own grounded probe.
