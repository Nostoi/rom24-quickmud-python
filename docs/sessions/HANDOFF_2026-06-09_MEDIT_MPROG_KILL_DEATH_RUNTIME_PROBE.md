# Handoff — 2026-06-09 — MEdit kill/death mobprog runtime probe

Read first:

1. `docs/sessions/SESSION_STATUS.md`
2. `docs/sessions/SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_KILL_DEATH_RUNTIME_PROBE.md`
3. `docs/parity/DIVERGENCE_CLASS_ROSTER.md`

What just landed:

- Added Class 11 dynamic coverage for the MEdit-created `kill` and `death`
  mobprog runtime paths. The new integration probe runs `_interpret_medit` for
  both triggers, spawns the edited `MobIndex`, and drives `apply_damage()` with
  deterministic lethal damage.
- The probe stubs only the mobprog program-flow sink and heavyweight death
  side effects (`group_gain`, `raw_kill`, auto-actions, wiznet), preserving the
  real MEdit → spawn → damage trigger boundary while keeping the assertion
  focused on trigger selection and order.
- No production parity gap was found; this is coverage expansion for the
  previous `TABLES-004` flag-value fix and the MEdit-created runtime trigger
  chain.
- Focused test result:
  `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_created_kill_and_death_triggers_fire_during_damage`
  — 1 passed.
- Area suite result:
  `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_combat_death.py tests/test_mobprog_triggers.py`
  — 69 passed.
- Lint result: `ruff check .` — clean.
- Full suite was not rerun in this session; previous baseline from the
  surrender-probe session was `PYTHONPATH=. pytest -q` — 5474 passed, 5 skipped.

Recommended next task:

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are an MEdit-created `exit` / `exall`
runtime probe or another non-RNG command path. Avoid RNG-locked combat until
seed alignment has its own grounded probe.
