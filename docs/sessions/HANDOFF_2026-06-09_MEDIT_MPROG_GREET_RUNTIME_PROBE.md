# Handoff — 2026-06-09 — MEdit greet mobprog runtime probe

Read first:

1. `docs/sessions/SESSION_STATUS.md`
2. `docs/sessions/SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_GREET_RUNTIME_PROBE.md`
3. `docs/parity/DIVERGENCE_CLASS_ROSTER.md`

What just landed:

- Added Class 11 dynamic coverage for the MEdit-created `greet` mobprog runtime
  path. The new integration probe runs `_interpret_medit("addmprog ... greet
  100")`, spawns the edited `MobIndex`, moves a PC into the spawned mob's room,
  and confirms `mp_greet_trigger` selects `Trigger.GREET` with the entering PC
  as actor.
- No production parity gap was found; this is coverage expansion for the
  previous `TABLES-004` flag-value fix and the `TRIG_ENTRY` runtime probe.
- Full suite result: `PYTHONPATH=. pytest -q` — 5468 passed, 5 skipped.
- Lint result: `ruff check .` — clean.

Recommended next task:

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. A good next probe is an OLC-created `speech` or
`act` mobprog reaching its runtime dispatch path, with a fresh ROM source read
first. Avoid RNG-locked combat until seed alignment has its own grounded probe.
