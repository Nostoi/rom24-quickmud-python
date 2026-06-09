# Handoff — 2026-06-09 — MEdit give mobprog runtime probe

Read first:

1. `docs/sessions/SESSION_STATUS.md`
2. `docs/sessions/SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_GIVE_RUNTIME_PROBE.md`
3. `docs/parity/DIVERGENCE_CLASS_ROSTER.md`

What just landed:

- Added Class 11 dynamic coverage for the MEdit-created `give` mobprog runtime
  path. The new integration probe runs `_interpret_medit("addmprog ... give
  relic")`, spawns the edited `MobIndex`, has a PC give a carried object to the
  spawned mob, and confirms the runtime `TRIG_GIVE` path selects the
  OLC-created `MobProgram` with the PC as actor and the object as `arg1`.
- The previous uncommitted MEdit-created `bribe` runtime probe is included in
  the same working tree and commit chain: `2.13.47` records `TRIG_BRIBE`, and
  `2.13.48` records `TRIG_GIVE`.
- No production parity gap was found; this is coverage expansion for the
  previous `TABLES-004` flag-value fix and the `TRIG_ENTRY` / `TRIG_GREET` /
  `TRIG_SPEECH` / `TRIG_ACT` / `TRIG_BRIBE` runtime probes.
- Full suite result: `PYTHONPATH=. pytest -q` — 5472 passed, 5 skipped.
- Area suite result:
  `PYTHONPATH=. pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_inv025_communication_act_trigger_dispatch.py tests/integration/test_npc_speaker_does_not_trigger_speech.py tests/integration/test_give_command.py tests/integration/test_mobprog_give_trigger.py tests/integration/test_inv025_do_give_act_trigger_suppression.py`
  — 64 passed.
- Lint result: `ruff check .` — clean.
- GitNexus result: `gitnexus_detect_changes(scope="all")` — low risk, no
  affected execution flows.

Recommended next task:

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. A good next probe is another OLC-created mobprog
runtime path that can be driven without RNG, or a non-combat lifecycle probe
with a clear ROM C source path. Avoid RNG-locked combat until seed alignment has
its own grounded probe.
