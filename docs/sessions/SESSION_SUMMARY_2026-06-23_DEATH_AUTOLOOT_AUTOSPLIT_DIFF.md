# Session Summary — 2026-06-23 — Death Autoloot Autosplit Differential Coverage

## Scope

Picked up from `SESSION_STATUS.md` after `death_autogold_autosplit`. The intended
death-lifecycle widening was grouped `PLR_AUTOLOOT` + `PLR_AUTOSPLIT` with mixed
corpse contents, using the existing `__plr_autoloot=0|1`, `__plr_autosplit=0|1`,
`__group_pc=<name>`, and mob inventory/coin meta-commands.

## Outcomes

### `death_autoloot_autosplit` — ✅ DIFFERENTIAL COVERAGE ADDED / FIGHT-080 FOLLOW-UP FIXED

- **Python**: `mud/commands/inventory.py:_get_obj`, `mud/commands/inventory.py:do_get`
- **ROM C**: `src/fight.c:945-957`, `src/act_obj.c:162-184`,
  `src/act_comm.c:1863-1981`
- **Gap**: `FIGHT-080` follow-up — `get_obj` autosplit updated balances but
  dropped the actor's returned `do_split` lines from `do_get` output.
- **Fix**: `_get_obj` now returns extra actor output alongside success/error
  state, and `do_get` appends that output after the matching "You get ..." line,
  mirroring ROM's `get_obj` → `do_split` ordering.
- **Coverage**:
  - Added `tools/diff_harness/scenarios/death_autoloot_autosplit.json`.
  - Captured `tests/data/golden/diff/death_autoloot_autosplit.golden.json`.
  - Scenario sets `PLR_AUTOLOOT` + `PLR_AUTOSPLIT`, creates a descriptorless
    grouped peer, kills a janitor with 17 silver, 2 gold, and a carried lantern,
    then verifies mixed corpse loot and autosplit output.
- **Result**: grouped death `PLR_AUTOLOOT` + `PLR_AUTOSPLIT` converges with ROM.
  The driver keeps 9 silver and 1 gold, the grouped peer receives 8 silver and
  1 gold, and the actor sees both ROM split lines after the corpse money line.

## Files Modified

- `mud/commands/inventory.py` — preserved `do_split` actor output from `get_obj`
  money autosplit and appended it from `do_get`.
- `tools/diff_harness/scenarios/death_autoloot_autosplit.json` — new scenario.
- `tests/data/golden/diff/death_autoloot_autosplit.golden.json` — C oracle golden.
- `tests/test_differential_smoke.py` — scenario-count comment refreshed.
- `docs/parity/FIGHT_C_AUDIT.md` — recorded the FIGHT-080 autosplit output
  follow-up.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the dynamic widening and
  caught divergence.
- `CHANGELOG.md` — added Unreleased coverage and fix entries.
- `pyproject.toml` — `2.14.214` → `2.14.215`.

## Test Status

- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k death_autoloot_autosplit` — skipped before the golden existed, then 1 passed after capture/fix.
- `cd src && make -f Makefile.diffshim diffshim` — C shim rebuilt.
- `PYTHONPATH=. python3 -m tools.diff_harness.capture --scenario death_autoloot_autosplit` — golden captured.
- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k 'death_autoloot_autosplit or death_autogold_autosplit'` — 2 passed.
- `PYTHONPATH=. pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — 88 passed.
- `ruff check mud/commands/inventory.py tests/test_differential_smoke.py` — clean.
- `ruff check .` — clean.
- `pytest` — 6042 passed, 4 skipped.
- `git diff --check` — clean.
- `python3 -m json.tool` on the new scenario and golden — valid JSON.

## Next Steps

Continue the cross-file invariant / differential-harness pass. A reasonable next
probe is a non-death `get all corpse` or container money autosplit replay, since
the fixed `do_get` extra-output path is shared beyond death auto-actions.
