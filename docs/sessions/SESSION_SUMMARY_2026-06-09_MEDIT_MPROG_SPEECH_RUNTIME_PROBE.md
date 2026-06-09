# Session Summary — 2026-06-09 — MEdit speech mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from the MEdit `TRIG_ENTRY`
and `TRIG_GREET` runtime probes. This session read the ROM `do_say` speech
trigger path and added coverage for an OLC-created `speech` mobprog reaching the
player-facing runtime dispatch path without changing production behavior.

## Outcomes

### MEdit-created `TRIG_SPEECH` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/act_comm.c:779-787`,
  `src/mob_prog.c:1183-1201`
- **Gap**: none found. The existing implementation already carries the
  builder-created `MobProgram` and `TRIG_SPEECH` bit into spawned NPC instances,
  and the player-facing `do_say` path reaches speech-trigger selection with the
  raw spoken phrase.
- **Coverage**: added
  `test_addmprog_created_speech_trigger_fires_when_pc_says_phrase`, which runs
  `_interpret_medit("addmprog ... speech secret")`, spawns the edited mob
  prototype, runs `do_say()` from a PC in the same room, and verifies the runtime
  speech trigger selects the OLC-created program with the PC speaker as actor.

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added the MEdit →
  spawn → `do_say` → speech trigger probe.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion.
- `CHANGELOG.md` — added `2.13.45` entry for the new dynamic coverage.
- `pyproject.toml` — `2.13.44` → `2.13.45`.

## Test Status

- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_speech_trigger_fires_when_pc_says_phrase`
  — 1 passed.
- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_inv025_communication_act_trigger_dispatch.py tests/integration/test_npc_speaker_does_not_trigger_speech.py`
  — 44 passed.
- `ruff check .` — clean.
- `PYTHONPATH=. pytest -q` — 5469 passed, 5 skipped.
- `gitnexus_detect_changes(scope="all")` — low risk, no affected execution
  flows.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. A good next probe is the sibling OLC-created `act`
mobprog runtime path, with a fresh ROM source read through the room `act()`
dispatch path first. Avoid RNG-locked combat until seed alignment has its own
grounded probe.
