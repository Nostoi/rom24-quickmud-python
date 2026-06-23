# Session Summary — 2026-06-22 — Death Autosplit Differential Coverage

## Scope

Picked up from `SESSION_STATUS.md` after `death_auto_sac`. The next intended
death-lifecycle probe was grouped reward `PLR_AUTOSPLIT`, with a prerequisite to
add deterministic grouped-PC setup to the differential harness if C-oracle
coverage needed it.

## Outcomes

### `death_autosac_autosplit` — ✅ DIFFERENTIAL COVERAGE ADDED

- **Python replay**: `tools/diff_harness/pyreplay.py`
- **ROM C shim**: `src/diff_shim/diffmain.c`
- **ROM C**: `src/fight.c:968-979`, `src/act_obj.c:1838-1853`,
  `src/act_comm.c:1863-1981`
- **Coverage**:
  - Added `__plr_autosplit=0|1` to both replay drivers.
  - Added `__group_pc=<name>` to both replay drivers. On the C side, the grouped
    peer is descriptorless so the single synthetic descriptor captures only the
    driver PC's output while still allowing state changes like split silver.
  - Committed `tools/diff_harness/scenarios/death_autosac_autosplit.json` and
    the C golden.
- **Result**: grouped death `PLR_AUTOSAC` + `PLR_AUTOSPLIT` converges with ROM.
  The golden asserts the driver receives 2 silver, the grouped peer receives 1
  silver, and the driver output includes the sacrifice + split lines. No engine
  behavior fix was needed.

## Files Modified

- `src/diff_shim/diffmain.c` — descriptorless grouped-PC setup and
  `__plr_autosplit=0|1`.
- `tools/diff_harness/pyreplay.py` — shared test-character setup,
  `__plr_autosplit=0|1`, and `__group_pc=<name>`.
- `tools/diff_harness/scenarios/death_autosac_autosplit.json` — new scenario.
- `tests/data/golden/diff/death_autosac_autosplit.golden.json` — C oracle
  golden.
- `tests/test_diff_harness_unit.py` — replay unit coverage for the new
  meta-commands.
- `tests/test_differential_smoke.py` — scenario-count comment refreshed.
- `tools/diff_harness/README.md` — documented the new meta-commands.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the dynamic widening.
- `CHANGELOG.md` — added Unreleased entry.
- `pyproject.toml` — `2.14.212` → `2.14.213`.

## Test Status

- `PYTHONPATH=. pytest -n0 tests/test_diff_harness_unit.py::test_drive_python_replay_plr_autosplit_meta_sets_flag tests/test_diff_harness_unit.py::test_drive_python_replay_group_pc_meta_adds_grouped_watched_pc` — 2 passed.
- `make -f Makefile.diffshim diffshim` — C shim rebuilt.
- `PYTHONPATH=. python3 -m tools.diff_harness.capture --scenario death_autosac_autosplit` — golden captured.
- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k death_autosac_autosplit` — 1 passed, 52 deselected.
- `PYTHONPATH=. pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — 86 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.
- `PYTHONPATH=. python3 -m tools.diff_harness.capture --check` — broad check
  reported many pre-existing scenario golden deltas, but
  `death_autosac_autosplit` was `ok`; no unrelated goldens were regenerated.
- `gitnexus_detect_changes()` — HIGH risk because the change touches central
  diff-harness entry points (`src/diff_shim/diffmain.c:main`,
  `tools/diff_harness/pyreplay.py:drive_python_replay`). Reviewed with
  `gitnexus_context`; affected surface is harness-only.

## Next Steps

Continue the active cross-file invariant / differential-harness pass. A natural
next death-lifecycle widening is plain `PLR_AUTOSPLIT` from `group_gain`
(`src/fight.c:1727-1800`) without the `do_sacrifice` autosac path, now that
`__group_pc=<name>` exists.
