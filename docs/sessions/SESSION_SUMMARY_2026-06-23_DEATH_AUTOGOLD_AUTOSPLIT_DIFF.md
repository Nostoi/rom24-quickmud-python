# Session Summary — 2026-06-23 — Death Autogold Autosplit Differential Coverage

## Scope

Picked up from `SESSION_STATUS.md` after `death_autosac_autosplit`. The intended
death-lifecycle widening was plain grouped `PLR_AUTOSPLIT` without the
`do_sacrifice` autosac path. The existing `__group_pc=<name>` and
`__plr_autosplit=0|1` meta-commands were sufficient.

## Outcomes

### `death_autogold_autosplit` — ✅ DIFFERENTIAL COVERAGE ADDED

- **ROM C**: `src/fight.c:968-979`, `src/act_obj.c:162-184`,
  `src/act_comm.c:1863-1981`
- **Coverage**:
  - Added `tools/diff_harness/scenarios/death_autogold_autosplit.json`.
  - Captured `tests/data/golden/diff/death_autogold_autosplit.golden.json`.
  - Scenario sets `PLR_AUTOGOLD` + `PLR_AUTOSPLIT`, creates a descriptorless
    grouped peer, kills a janitor with 17 silver, and verifies the corpse-money
    autogold path triggers ROM autosplit.
- **Result**: grouped death `PLR_AUTOGOLD` + `PLR_AUTOSPLIT` converges with ROM.
  The driver keeps 9 silver, the grouped peer receives 8 silver, and no engine
  behavior fix was needed.

## Files Modified

- `tools/diff_harness/scenarios/death_autogold_autosplit.json` — new scenario.
- `tests/data/golden/diff/death_autogold_autosplit.golden.json` — C oracle golden.
- `tests/test_differential_smoke.py` — scenario-count comment refreshed.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the dynamic widening.
- `docs/sessions/SESSION_STATUS.md` — moved the canonical pointer to this summary.
- `CHANGELOG.md` — added Unreleased entry.
- `pyproject.toml` — `2.14.213` → `2.14.214`.

## Test Status

- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k death_autogold_autosplit` — skipped before the golden existed.
- `cd src && make -f Makefile.diffshim diffshim` — C shim rebuilt.
- `PYTHONPATH=. python3 -m tools.diff_harness.capture --scenario death_autogold_autosplit` — golden captured.
- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k death_autogold_autosplit` — 1 passed, 53 deselected.

## Next Steps

Continue the active cross-file invariant / differential-harness pass. A natural
next death-lifecycle widening is grouped `PLR_AUTOLOOT` + `PLR_AUTOSPLIT` with
mixed corpse contents.
