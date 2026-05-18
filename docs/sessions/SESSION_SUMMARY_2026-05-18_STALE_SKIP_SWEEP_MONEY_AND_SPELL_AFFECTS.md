# Session Summary — 2026-05-18 — stale skip sweep in money + spell affect integrations

## What landed

- Replaced stale skipped money-drop placeholders in `tests/integration/test_money_objects.py` with ROM-accurate executable coverage.
  - `drop 15 silver` now verifies the ROM `do_drop` behavior from `src/act_obj.c:541-589`: room money piles are consolidated before the new pile is created.
  - `drop 1 silver` with no funds now verifies the ROM early-return message.
- Replaced stale skipped spell-affect placeholders in `tests/integration/test_spell_affects_persistence.py` with executable integration tests for:
  - cursed item removal lockout
  - poison damage-over-time through `game_tick()`
  - plague contagion through `char_update()`

## Real parity bug found and fixed

- The stale-skip sweep exposed a real bug in `mud/game_loop.py`.
- ROM `src/update.c:839-840` spreads plague by applying a full new affect record to each infected victim.
- Python was calling `add_affect(AffectData)` on the spread victim instead of attaching the affect record through the ROM-style path.
- Fixed by switching the contagion path to `affect_to_char(new_af)` with a defensive fallback for test doubles.

## Files touched

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_money_objects.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_spell_affects_persistence.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/INTEGRATION_TEST_COVERAGE_TRACKER.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`

## Verification

- `./venv/bin/python -m pytest -q tests/integration/test_spell_affects_persistence.py -k 'curse_prevents_item_removal or poison_damages_over_time or plague_spreads_to_nearby_characters'` → `3 passed`
- `./venv/bin/python -m pytest -q tests/integration/test_money_objects.py -k 'drop_command'` → `2 passed`
- `./venv/bin/python -m pytest -q tests/integration/test_update_c_parity.py -k 'poison or plague'` → `2 passed`
- `./venv/bin/python -m pytest -q tests/integration/test_remove_command.py -k 'noremove or remove'` → `6 passed`
- `./venv/bin/python -m pytest -q tests/integration/test_money_objects.py tests/integration/test_spell_affects_persistence.py` → `42 passed`
- `./venv/bin/ruff check mud/game_loop.py tests/integration/test_money_objects.py tests/integration/test_spell_affects_persistence.py` → clean

## Result

- The spell-affects persistence slice is now fully green at `21/21`.
- The money-object drop slice no longer carries stale “not implemented” skips.
- The next task is to continue scanning the remaining integration skip markers for the next live gap instead of historical drift.
