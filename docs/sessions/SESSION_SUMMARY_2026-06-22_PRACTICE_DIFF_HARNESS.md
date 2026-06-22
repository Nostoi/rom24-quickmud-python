# Session Summary — 2026-06-22 — Practice differential harness widening

## Scope

Resumed the differential-harness widening track from `SESSION_STATUS.md`. The
target was the `practice` surface: add a partial learned-percent meta-command so
the harness can drive ROM `do_practice` below adept, then add a C-oracle
scenario covering the INT learn-rate increment and known-skill listing path.

## Outcomes

### `practice_skill_listing` differential — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/practice_skill_listing.json`
- **Golden**: `tests/data/golden/diff/practice_skill_listing.golden.json`
- **ROM C**: `src/act_info.c:2680-2794` (`do_practice`), especially
  `int_app[get_curr_stat(ch, STAT_INT)].learn / rating` at `2772-2774`.
- **Harness support**: added `__learn_pct=NAME=N` to both
  `src/diff_shim/diffmain.c` and `tools/diff_harness/pyreplay.py`.
- **Coverage**: the scenario starts a level-7 default mage, `__mload`s the
  Midgaard mage guildmaster (`3020`, `ACT_PRACTICE`), seeds `armor` at 1%, runs
  `practice armor`, then runs bare `practice`.
- **Observed C oracle**: `armor` advances from 1% to 35% for the default INT-16
  mage, and practice sessions drop from 5 to 4. Python replay converges.

### Mud School wimpy-aggressive report — ✅ ROM-CORRECT

- User observed the Mud School wimpy aggressive monster not attacking a standing
  level-2 PC.
- ROM `src/update.c:1106` skips aggressive mobs with `ACT_WIMPY` when the
  watched PC is awake; standing is awake. Python mirrors this at
  `mud/ai/aggressive.py:94`.
- No code change required. Verified existing aggressive/wimpy tests.

## Files Modified

- `src/diff_shim/diffmain.c` — C shim support for `__learn_pct=NAME=N`.
- `tools/diff_harness/pyreplay.py` — Python replay support for
  `__learn_pct=NAME=N`.
- `tools/diff_harness/README.md` — documented the new meta-command.
- `tools/diff_harness/scenarios/practice_skill_listing.json` — new scenario.
- `tests/data/golden/diff/practice_skill_listing.golden.json` — new ROM C
  golden.
- `tests/test_diff_harness_unit.py` — unit guard for partial-skill meta output.
- `tests/test_differential_smoke.py` — refreshed scenario-count comment.
- `CHANGELOG.md` — added release note.
- `pyproject.toml` — 2.14.205 → 2.14.206.
- `docs/sessions/SESSION_STATUS.md` — advanced current pointer and next task.

## Test Status

- `PYTHONPATH=. pytest -q tests/test_diff_harness_unit.py::test_drive_python_replay_learn_pct_meta_sets_partial_skill 'tests/test_differential_smoke.py::test_python_matches_c_golden[practice_skill_listing]'`
  — 2 passed.
- `PYTHONPATH=. pytest -q tests/test_differential_smoke.py tests/test_diff_harness_unit.py`
  — 77 passed.
- Additional pre-commit verification is recorded in the handoff for this
  session.

## Next Steps

Continue widening the death/autoloot differential surface:

- **FIGHT-079** — PC corpse half-coin gate (`src/fight.c:1483-1495`): ROM drops
  half the coins for non-clan PC corpses; Python currently drops full + zeroes.
  Close as a separate gap-closer commit with a PC-victim corpse-money test.
- **Auto-loot / auto-gold death scenarios** — add PLR_AUTOLOOT/AUTOGOLD harness
  meta support; `death_corpse_loot_sacrifice` only covers manual
  corpse→get→sacrifice.
