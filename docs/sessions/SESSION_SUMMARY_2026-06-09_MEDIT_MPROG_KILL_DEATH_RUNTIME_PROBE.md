# Session Summary — 2026-06-09 — MEdit kill/death mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from the MEdit `TRIG_ENTRY`,
`TRIG_GREET`, `TRIG_SPEECH`, `TRIG_ACT`, `TRIG_BRIBE`, `TRIG_GIVE`,
`TRIG_FIGHT`/`TRIG_HPCNT`, and `TRIG_SURR` runtime probes. This session read
the ROM `damage()` kill/death trigger path and added coverage for OLC-created
`kill` and `death` mobprogs reaching the runtime dispatch path without changing
production behavior.

## Outcomes

### MEdit-created `TRIG_KILL` / `TRIG_DEATH` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/fight.c:740-741`,
  `src/fight.c:918-921`
- **Gap**: none found. The existing implementation already carries
  builder-created `MobProgram` rows and ROM trigger bits into spawned NPC
  instances, and the `apply_damage()` path selects `TRIG_KILL` when the NPC
  victim first enters combat and `TRIG_DEATH` after lethal damage before
  `raw_kill`.
- **Coverage**: added
  `test_addmprog_created_kill_and_death_triggers_fire_during_damage`, which
  runs `_interpret_medit("addmprog ... kill 100")` and
  `_interpret_medit("addmprog ... death 100")`, spawns the edited mob
  prototype, applies deterministic lethal damage from a PC attacker, and
  verifies the runtime kill/death trigger order and actor binding.

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added the MEdit →
  spawn → `apply_damage` → kill/death-trigger probe.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion.
- `CHANGELOG.md` — added `2.13.51` entry for the new dynamic coverage.
- `pyproject.toml` — `2.13.50` → `2.13.51`.
- `docs/sessions/SESSION_STATUS.md` — refreshed the current pointer.
- `docs/sessions/HANDOFF_2026-06-09_MEDIT_MPROG_KILL_DEATH_RUNTIME_PROBE.md` —
  added next-session handoff notes.

## Test Status

- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_kill_and_death_triggers_fire_during_damage`
  — 1 passed.
- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_combat_death.py tests/test_mobprog_triggers.py`
  — 69 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.
- Full suite not rerun this session; previous session baseline was
  `PYTHONPATH=. pytest -q` — 5474 passed, 5 skipped.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are an `exit` / `exall` MEdit-created
mobprog runtime probe or another non-RNG command path. Avoid RNG-locked combat
until seed alignment has its own grounded probe.
