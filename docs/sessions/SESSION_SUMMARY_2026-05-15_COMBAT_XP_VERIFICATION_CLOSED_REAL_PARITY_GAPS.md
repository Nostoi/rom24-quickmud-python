# Session Summary — 2026-05-15 — combat→XP verification closed real parity gaps

## Goal

Complete the planned ROM-source-first verification pass for the combat → XP advancement flow after the full-suite recertification.

## ROM sources used

- `src/fight.c`
  - `group_gain`
  - `xp_compute`
  - death branch inside `damage`
  - `raw_kill`
- `src/update.c`
  - `advance_level`
  - `gain_exp`

## What this session found

This verification pass did not stop at the first green test. It found and closed three real parity issues:

1. **Missing player death XP penalty in the combat death path**
   - ROM applies the penalty in `fight.c` after `group_gain()` and before `raw_kill()`.
   - Python was killing the player without applying that penalty.

2. **Wrong `gain_exp()` level-up side-effect order**
   - ROM sends `"You raise a level!!"` before `advance_level()`.
   - Python sent the banner after `advance_level()`, so the stat-gain message arrived first.

3. **Missing ROM level-gain logging + wrong integer division semantics in `xp_compute()`**
   - ROM logs `"%s gained level %d"` before wiznet during level-up.
   - Python skipped that log entirely.
   - `xp_compute()` still used Python `//` in ROM-sensitive arithmetic, including a negative intermediate where C truncates toward zero.

## Code changes

### Production

- `mud/combat/engine.py`
  - `_handle_death()` now applies the ROM player death XP penalty before `raw_kill()`.

- `mud/advancement.py`
  - `gain_exp()` now:
    - sends the level-up banner before `advance_level()`
    - logs `"<name> gained level <n>"` via `mud.logging.log_game_event`
    - wiznets after the log and before save, matching ROM ordering

- `mud/groups/xp.py`
  - `xp_compute()` now uses `c_div(...)` throughout ROM-sensitive integer math
  - this fixes negative truncation behavior and aligns the XP path with C semantics

### Tests added/expanded

- `tests/integration/test_character_advancement.py`
  - `test_player_kill_applies_rom_death_penalty`

- `tests/test_advancement.py`
  - `test_gain_exp_sends_level_message_before_advance_level_gains`
  - `test_gain_exp_logs_level_gain_before_wiznet`
  - `test_xp_compute_alignment_change_uses_c_truncation`

## Verification run

Targeted regression proof:

- `./venv/bin/python -m pytest -q tests/test_advancement.py -k 'level_message_before or logs_level_gain_before_wiznet or c_truncation' tests/integration/test_character_advancement.py::test_player_kill_applies_rom_death_penalty`
- result: `3 passed, 15 deselected`

Broader slice verification:

- `./venv/bin/python -m pytest -q tests/test_advancement.py tests/integration/test_character_advancement.py tests/integration/test_death_and_corpses.py tests/test_combat_death.py`
- result: `77 passed in 23.58s`

## Docs updated

- `docs/parity/FIGHT_C_AUDIT.md`
  - added `FIGHT-003` closure for player death XP penalty before `raw_kill()`

- `docs/parity/UPDATE_C_AUDIT.md`
  - refreshed scope to include `mud/advancement.py`
  - added `GL-022` / `GL-023` closure notes for `gain_exp()` / `advance_level()` XP-path behavior

- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
  - refreshed `fight.c` and `update.c` tracker notes

- `docs/sessions/SESSION_STATUS.md`
  - updated current state and next-task pointer

## Outcome

The combat → XP verification slice is now closed with test-backed evidence. The remaining item on this slice is only the intentionally deferred minor `GL-021` (`wiznet("TICK!")`).
