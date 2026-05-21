# Session Summary — 2026-05-21 — `act_info.c` trust rebuild: `do_who`

## What landed

Continued the `act_info.c` trust-rebuild with `do_who`.

This slice found one real parity bug and tightened the test surface from broad
matrix checks toward ROM-exact line assertions.

## Real bug fixed

### `do_who` ignored switched descriptors

ROM iterates descriptors and uses:
- `wch = (d->original != NULL) ? d->original : d->character;`

The Python implementation always used the active session character, which meant
switched immortals displayed as their shell rather than the controlling player.
It also sourced title text from `title` directly instead of `pcdata.title`.

Fixed in:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/info.py`

## Test tightening

Updated:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_do_who_command.py`

Added:
- exact switched-session output assertion
- exact representative flagged-player line assertion

## Verification

- `./venv/bin/python -m pytest -q tests/integration/test_do_who_command.py`
- Result: `22 passed`

- broader current `act_info.c` band:
  - `tests/integration/test_do_who_command.py`
  - `tests/integration/test_do_where_command.py`
  - `tests/integration/test_do_inventory.py`
  - `tests/integration/test_do_equipment.py`
  - `tests/test_player_info_commands.py`
  - `tests/test_act_info_rom_parity.py`
- Result: `88 passed`

## Next step

Move to `do_look`, which is now the highest-value remaining `act_info.c`
trust-rebuild surface because it is the most user-visible command and still has
high complexity relative to the current evidence quality.
