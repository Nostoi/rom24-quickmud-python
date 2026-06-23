# Handoff — 2026-06-23 — Death autoloot autosplit differential coverage

## Current Branch State

- Version: **2.14.215**
- Differential scenarios: **55 / 55 converge**, `KNOWN_DIVERGENCES` empty.
- Latest completed focus: grouped `PLR_AUTOLOOT` + `PLR_AUTOSPLIT` death
  auto-action coverage with mixed NPC corpse contents.

## What Changed

- New scenario and C golden:
  - `death_autoloot_autosplit`

- Coverage result:
  - ROM `damage()` calls `do_get(ch, "all corpse")` for `PLR_AUTOLOOT`.
  - ROM `get_obj` then calls `do_split` when the looted money object sees
    `PLR_AUTOSPLIT`.
  - Python initially matched balances but dropped the actor's split output.
  - `mud.commands.inventory._get_obj` / `do_get` now preserves those actor lines
    after the "You get ..." money line.

## Verification Already Run

- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k death_autoloot_autosplit` — 1 passed after capture/fix.
- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k 'death_autoloot_autosplit or death_autogold_autosplit'` — 2 passed.
- `PYTHONPATH=. pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — 88 passed.
- `ruff check mud/commands/inventory.py tests/test_differential_smoke.py` — clean.
- `ruff check .` — clean.
- `pytest` — 6042 passed, 4 skipped.
- `git diff --check` — clean.
- `python3 -m json.tool` on the new scenario and golden — valid JSON.

## Suggested Next Probe

Exercise the same `do_get` money-autosplit output path outside death auto-actions,
for example a direct `get all corpse` or get-from-container money scenario. Re-read
ROM `src/act_obj.c:92-193` and `src/act_comm.c:1863-1981` before changing behavior.
