# Handoff — 2026-06-09 — MEdit speech mobprog runtime probe

Read first:

1. `docs/sessions/SESSION_STATUS.md`
2. `docs/sessions/SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_SPEECH_RUNTIME_PROBE.md`
3. `docs/parity/DIVERGENCE_CLASS_ROSTER.md`

What just landed:

- Added Class 11 dynamic coverage for the MEdit-created `speech` mobprog
  runtime path. The new integration probe runs `_interpret_medit("addmprog ...
  speech secret")`, spawns the edited `MobIndex`, has a PC say a matching raw
  phrase, and confirms the runtime speech trigger selects the OLC-created
  `MobProgram` with the PC speaker as actor.
- No production parity gap was found; this is coverage expansion for the
  previous `TABLES-004` flag-value fix and the `TRIG_ENTRY` / `TRIG_GREET`
  runtime probes.
- Full suite result: `PYTHONPATH=. pytest -q` — 5469 passed, 5 skipped.
- Lint result: `ruff check .` — clean.
- GitNexus result: `gitnexus_detect_changes(scope="all")` — low risk, no
  affected execution flows.

Recommended next task:

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. A good next probe is an OLC-created `act` mobprog
reaching its runtime dispatch path, with a fresh ROM source read first. Avoid
RNG-locked combat until seed alignment has its own grounded probe.
