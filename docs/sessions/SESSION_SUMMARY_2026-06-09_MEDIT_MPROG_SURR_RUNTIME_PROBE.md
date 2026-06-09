# Session Summary — 2026-06-09 — MEdit surrender mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from the MEdit `TRIG_ENTRY`,
`TRIG_GREET`, `TRIG_SPEECH`, `TRIG_ACT`, `TRIG_BRIBE`, `TRIG_GIVE`, and
`TRIG_FIGHT`/`TRIG_HPCNT` runtime probes. This session read the ROM
`do_surrender` surrender-trigger path and added coverage for an OLC-created
`surr` mobprog reaching the player-facing runtime dispatch path without
changing production behavior.

## Outcomes

### MEdit-created `TRIG_SURR` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/fight.c:3235-3237`
- **Gap**: none found. The existing implementation already carries the
  builder-created `MobProgram` and `TRIG_SURR` bit into spawned NPC instances,
  and the player-facing `do_surrender` path reaches surrender-trigger selection
  before ROM's NPC ignore/retaliation fallback.
- **Coverage**: added
  `test_addmprog_created_surr_trigger_fires_when_pc_surrenders`, which runs
  `_interpret_medit("addmprog ... surr 100")`, spawns the edited mob prototype,
  puts a PC and the spawned NPC into combat, runs `do_surrender()`, and verifies
  the runtime surrender trigger selects the OLC-created program with the PC as
  actor.

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added the MEdit →
  spawn → `do_surrender` → surrender-trigger probe.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion.
- `CHANGELOG.md` — added `2.13.50` entry for the new dynamic coverage.
- `pyproject.toml` — `2.13.49` → `2.13.50`.
- `docs/sessions/SESSION_STATUS.md` — refreshed the current pointer.
- `docs/sessions/HANDOFF_2026-06-09_MEDIT_MPROG_SURR_RUNTIME_PROBE.md` —
  added next-session handoff notes.

## Test Status

- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_surr_trigger_fires_when_pc_surrenders`
  — 1 passed.
- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_combat_surrender.py tests/integration/test_surrender_broadcasts.py tests/test_mobprog_triggers.py`
  — 51 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.
- `PYTHONPATH=. pytest -q` — 5474 passed, 5 skipped.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are MEdit-created `death` / `kill`
runtime probes or an exit/exall probe that avoids relying on movement RNG.
Avoid RNG-locked combat until seed alignment has its own grounded probe.
