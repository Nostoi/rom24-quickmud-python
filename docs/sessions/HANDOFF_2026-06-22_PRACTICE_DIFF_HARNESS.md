# Handoff — 2026-06-22 — Practice differential harness widening

Read first:

1. `docs/sessions/SESSION_STATUS.md`
2. `docs/sessions/SESSION_SUMMARY_2026-06-22_PRACTICE_DIFF_HARNESS.md`
3. `tools/diff_harness/README.md`

What just landed:

- Added `__learn_pct=NAME=N` to both differential harness drivers:
  `src/diff_shim/diffmain.c` and `tools/diff_harness/pyreplay.py`.
- Added `practice_skill_listing`, a ROM C golden-backed scenario that loads the
  Midgaard mage guildmaster (`3020`, `ACT_PRACTICE`), seeds `armor` at 1%, runs
  `practice armor`, then lists known skills. ROM and Python converge with
  `armor` at 35% and 4 practice sessions left.
- Confirmed the user-observed Mud School wimpy aggressive monster behavior is
  ROM-correct: `ACT_WIMPY` aggressive mobs skip awake PCs.

Verification completed:

- `cd src && make -f Makefile.diffshim diffshim` — rebuilt C shim.
- `python3 -m tools.diff_harness.capture --scenario practice_skill_listing` —
  wrote the new golden.
- `PYTHONPATH=. pytest -q tests/test_diff_harness_unit.py::test_drive_python_replay_learn_pct_meta_sets_partial_skill 'tests/test_differential_smoke.py::test_python_matches_c_golden[practice_skill_listing]'`
  — 2 passed.
- `PYTHONPATH=. pytest -q tests/test_differential_smoke.py tests/test_diff_harness_unit.py`
  — 77 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.
- `gitnexus_detect_changes(scope="all")` — low risk; no affected execution
  flows.

Recommended next task:

Continue death/autoloot differential widening. Start with **FIGHT-079** (PC
corpse half-coin gate in `src/fight.c:1483-1495`) as its own gap-closer commit,
then add PLR_AUTOLOOT/AUTOGOLD meta support for auto-loot / auto-gold death
scenarios.
