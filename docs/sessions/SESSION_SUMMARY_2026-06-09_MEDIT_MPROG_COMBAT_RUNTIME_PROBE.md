# Session Summary — 2026-06-09 — MEdit combat mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from the MEdit `TRIG_ENTRY`,
`TRIG_GREET`, `TRIG_SPEECH`, `TRIG_ACT`, `TRIG_BRIBE`, and `TRIG_GIVE` runtime
probes. This session read the ROM `violence_update` combat-trigger path and
added coverage for OLC-created `fight` / `hpcnt` mobprogs reaching the
post-round runtime dispatch site without relying on combat RNG.

## Outcomes

### MEdit-created `TRIG_FIGHT` / `TRIG_HPCNT` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/fight.c:84-98`,
  `src/mob_prog.c:1355-1367`
- **Gap**: none found. The existing implementation already carries
  builder-created combat `MobProgram` rows into spawned NPC instances, and
  `violence_tick` dispatches `TRIG_FIGHT` before `TRIG_HPCNT` after
  `multi_hit` / `check_assist`, matching ROM's `violence_update` order.
- **Coverage**: added
  `test_addmprog_created_fight_and_hpcnt_triggers_fire_during_violence_tick`,
  which runs `_interpret_medit("addmprog ... fight 100")` and
  `_interpret_medit("addmprog ... hpcnt 50")`, spawns the edited mob prototype,
  stubs `multi_hit` / `check_assist` to keep the probe deterministic, and
  verifies the runtime trigger selection receives the fighting PC actor in ROM
  dispatch order.

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added the MEdit →
  spawn → `violence_tick` combat-trigger probe.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion.
- `CHANGELOG.md` — added `2.13.49` entry for the new dynamic coverage.
- `pyproject.toml` — `2.13.48` → `2.13.49`.
- `docs/sessions/SESSION_STATUS.md` — refreshed the current pointer.

## Test Status

- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_fight_and_hpcnt_triggers_fire_during_violence_tick`
  — 1 passed.
- `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_hpcnt_once_per_pulse.py tests/integration/test_check_assist_dispatch_scope.py`
  — 49 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.
- `PYTHONPATH=. pytest -q` — 5473 passed, 5 skipped.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are another OLC-created mobprog
trigger family that can be driven without RNG, or a non-combat lifecycle probe
that already has a clear ROM source path. Avoid RNG-locked combat until seed
alignment has its own grounded probe.
