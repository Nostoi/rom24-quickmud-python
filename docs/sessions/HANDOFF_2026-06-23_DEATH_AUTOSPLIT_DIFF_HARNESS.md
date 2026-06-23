# Handoff — 2026-06-23 — Death autosplit differential harness

## Current Branch State

- Version: **2.14.214**
- Differential scenarios: **54 / 54 converge**, `KNOWN_DIVERGENCES` empty.
- Latest completed focus: death auto-action widening for `PLR_AUTOSAC`,
  grouped `PLR_AUTOSAC` + `PLR_AUTOSPLIT`, and grouped `PLR_AUTOGOLD` +
  `PLR_AUTOSPLIT`.

## What Changed

- New harness meta commands:
  - `__plr_autosac=0|1`
  - `__plr_autosplit=0|1`
  - `__group_pc=NAME`

- New scenarios and C goldens:
  - `death_auto_sac`
  - `death_autosac_autosplit`
  - `death_autogold_autosplit`

- Coverage result:
  - Empty-NPC-corpse `PLR_AUTOSAC` converges with ROM.
  - Grouped `PLR_AUTOSAC` + `PLR_AUTOSPLIT` converges with ROM: the driver sees
    sacrifice/split output and keeps 2 silver; grouped peer receives 1 silver.
  - Grouped `PLR_AUTOGOLD` + `PLR_AUTOSPLIT` converges with ROM
    `src/act_obj.c:162-184`: the driver keeps 9 silver from 17 and the grouped
    peer receives 8 silver.

## Verification Already Run

- `PYTHONPATH=. pytest -n0 tests/test_diff_harness_unit.py::test_drive_python_replay_plr_autosplit_meta_sets_flag tests/test_diff_harness_unit.py::test_drive_python_replay_group_pc_meta_adds_grouped_watched_pc` — 2 passed.
- `cd src && make -f Makefile.diffshim diffshim` — C shim rebuilt.
- `PYTHONPATH=. python3 -m tools.diff_harness.capture --scenario death_autosac_autosplit` — golden captured.
- `PYTHONPATH=. python3 -m tools.diff_harness.capture --scenario death_autogold_autosplit` — golden captured.
- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k death_autosac_autosplit` — 1 passed.
- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k death_autogold_autosplit` — 1 passed.
- `PYTHONPATH=. pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — 87 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.

## Suggested Next Probe

Add grouped `PLR_AUTOLOOT` + `PLR_AUTOSPLIT` coverage with mixed corpse contents.
Re-read ROM `src/fight.c:945-980`, `src/act_obj.c:92-193`, and
`src/act_comm.c:1863-1981` before changing behavior; `get_obj` autosplit only
runs for money objects, so mixed contents should prove the `do_get all corpse`
path without assuming every looted object participates in split.
