# Handoff — 2026-06-09 — MEdit combat mobprog runtime probe

Read first:

1. `docs/sessions/SESSION_STATUS.md`
2. `docs/sessions/SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_COMBAT_RUNTIME_PROBE.md`
3. `docs/parity/DIVERGENCE_CLASS_ROSTER.md`

What just landed:

- Added Class 11 dynamic coverage for MEdit-created `fight` and `hpcnt` mobprog
  runtime paths. The new integration probe runs `_interpret_medit("addmprog ...
  fight 100")` and `_interpret_medit("addmprog ... hpcnt 50")`, spawns the
  edited `MobIndex`, sets up an NPC-vs-PC fighting pair, and drives
  `violence_tick(do_combat=True)`.
- The probe stubs `multi_hit` and `check_assist` so it pins ROM's deterministic
  post-round trigger site without depending on hit rolls, damage, or combat RNG.
- No production parity gap was found; this is coverage expansion for the earlier
  `TABLES-004` flag-value fix and the MEdit-created runtime trigger chain.
- Full suite result: `PYTHONPATH=. pytest -q` — 5473 passed, 5 skipped.
- Area suite result:
  `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_hpcnt_once_per_pulse.py tests/integration/test_check_assist_dispatch_scope.py`
  — 49 passed.
- Lint result: `ruff check .` — clean.

Recommended next task:

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Avoid RNG-locked combat until seed alignment has its
own grounded probe.
