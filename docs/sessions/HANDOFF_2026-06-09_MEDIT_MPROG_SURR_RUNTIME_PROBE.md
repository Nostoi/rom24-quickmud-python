# Handoff — 2026-06-09 — MEdit surrender mobprog runtime probe

Read first:

1. `docs/sessions/SESSION_STATUS.md`
2. `docs/sessions/SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_SURR_RUNTIME_PROBE.md`
3. `docs/parity/DIVERGENCE_CLASS_ROSTER.md`

What just landed:

- Added Class 11 dynamic coverage for the MEdit-created `surr` mobprog runtime
  path. The new integration probe runs `_interpret_medit("addmprog ... surr
  100")`, spawns the edited `MobIndex`, puts a PC and the spawned NPC into
  combat, and drives the player-facing `do_surrender()` command.
- The probe stubs only the mobprog program-flow sink and the percent roll,
  preserving the real MEdit → spawn → command boundary while making trigger
  selection deterministic.
- No production parity gap was found; this is coverage expansion for the
  previous `TABLES-004` flag-value fix and the MEdit-created runtime trigger
  chain.
- Full suite result: `PYTHONPATH=. pytest -q` — 5474 passed, 5 skipped.
- Area suite result:
  `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_combat_surrender.py tests/integration/test_surrender_broadcasts.py tests/test_mobprog_triggers.py`
  — 51 passed.
- Lint result: `ruff check .` — clean.

Recommended next task:

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are MEdit-created `death` / `kill`
runtime probes or an exit/exall probe that avoids relying on movement RNG.
Avoid RNG-locked combat until seed alignment has its own grounded probe.
