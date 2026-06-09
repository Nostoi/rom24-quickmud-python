# Handoff — 2026-06-09 — MEdit act mobprog runtime probe

Read first:

1. `docs/sessions/SESSION_STATUS.md`
2. `docs/sessions/SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_ACT_RUNTIME_PROBE.md`
3. `docs/parity/DIVERGENCE_CLASS_ROSTER.md`

What just landed:

- Added Class 11 dynamic coverage for the MEdit-created `act` mobprog runtime
  path. The new integration probe runs `_interpret_medit("addmprog ... act
  stands up")`, spawns the edited `MobIndex`, has a resting PC stand in the
  same room, and confirms the runtime `TRIG_ACT` path selects the OLC-created
  `MobProgram` with the PC as actor.
- No production parity gap was found; this is coverage expansion for the
  previous `TABLES-004` flag-value fix and the `TRIG_ENTRY` / `TRIG_GREET` /
  `TRIG_SPEECH` runtime probes.
- Full suite result: `PYTHONPATH=. pytest -q` — 5470 passed, 5 skipped.
- Lint result: `ruff check .` — clean.
- GitNexus result: `gitnexus_detect_changes(scope="all")` — low risk, no
  affected execution flows.

Recommended next task:

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. A good next probe is another OLC-created mobprog
runtime path that can be driven without RNG, or a non-combat lifecycle probe
with a clear ROM C source path. Avoid RNG-locked combat until seed alignment has
its own grounded probe.
