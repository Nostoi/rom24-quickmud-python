# Session Summary — 2026-06-09 — MEdit act mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from the MEdit `TRIG_ENTRY`,
`TRIG_GREET`, and `TRIG_SPEECH` runtime probes. This session read the ROM
`act()` / `mp_act_trigger` path and added coverage for an OLC-created `act`
mobprog reaching the player-facing runtime dispatch path without changing
production behavior.

## Outcomes

### MEdit-created `TRIG_ACT` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/act_move.c:1062`,
  `src/comm.c:2384-2385`, `src/mob_prog.c:1183-1201`
- **Gap**: none found. The existing implementation already carries the
  builder-created `MobProgram` and `TRIG_ACT` bit into spawned NPC instances,
  and the `do_stand` act-line path reaches act-trigger selection with the
  rendered room line.
- **Coverage**: added
  `test_addmprog_created_act_trigger_fires_when_pc_stands`, which runs
  `_interpret_medit("addmprog ... act stands up")`, spawns the edited mob
  prototype, runs `do_stand()` from a resting PC in the same room, and verifies
  the runtime act trigger selects the OLC-created program with the PC as actor.

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added the MEdit →
  spawn → `do_stand` → act-trigger probe.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion.
- `CHANGELOG.md` — added `2.13.46` entry for the new dynamic coverage.
- `pyproject.toml` — `2.13.45` → `2.13.46`.
- `docs/sessions/SESSION_STATUS.md` — refreshed the current pointer.

## Test Status

- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_act_trigger_fires_when_pc_stands`
  — 1 passed.
- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_inv025_communication_act_trigger_dispatch.py tests/integration/test_npc_speaker_does_not_trigger_speech.py`
  — 45 passed.
- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_inv025_communication_act_trigger_dispatch.py tests/integration/test_npc_speaker_does_not_trigger_speech.py`
  — 45 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.
- `PYTHONPATH=. pytest -q` — 5470 passed, 5 skipped.
- `gitnexus_detect_changes(scope="all")` — low risk, no affected execution
  flows.

## Notes

The first default-parallel run of the four-file OLC/mobprog slice reported a
transient miss of the `death` event in
`tests/test_mobprog_triggers.py::test_event_hooks_fire_rom_triggers`. The test
passed when isolated with `-n0`, the full four-file slice passed with `-n0`, and
the default-parallel four-file slice passed on immediate re-run. No production
code was changed.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are another OLC-created mobprog
trigger family that can be driven without RNG, or a non-combat lifecycle probe
that already has a clear ROM source path. Avoid RNG-locked combat until seed
alignment has its own grounded probe.
