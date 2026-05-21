# Session Summary — 2026-05-21 — `act_info.c` trust rebuild: `equipment`, `inventory`, `where`

## What landed

Continued the `act_info.c` trust-rebuild with the next player-visible surfaces:
- `do_equipment`
- `do_inventory`
- `do_where`

This slice found two real parity bugs and converted one inventory surface from
substring-only coverage to exact layout coverage.

## Real bugs fixed

### 1. `do_equipment` used Python dict insertion order instead of ROM wear-slot order

ROM iterates equipment with:
- `for (iWear = 0; iWear < MAX_WEAR; iWear++)`

The Python implementation iterated `char.equipment.items()`, which meant the
render order depended on insertion order rather than ROM slot order.

Fixed in:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/inventory.py`

### 2. `do_where` mode 1 skipped the ROM private-room gate on the live session path

The implementation still had a TODO where ROM requires:
- `is_room_owner(ch, victim->in_room) || !room_is_private(victim->in_room)`

That meant mortals could see descriptor-backed players in genuinely private
rooms when the room had enough occupants to be private under ROM rules.

Fixed in:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/info.py`

## Test tightening

### `do_equipment`
Updated:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_do_equipment.py`

Added exact ROM-order coverage that intentionally reverses dict insertion order
and asserts the rendered slot order still follows ROM wear-slot order.

### `do_inventory`
Updated:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_do_inventory.py`

Added an exact combined-output assertion for a small mixed inventory layout.
This surface did not require a code fix in this slice.

### `do_where`
Updated:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_do_where_command.py`

Added a descriptor/session-backed private-room regression that matches ROM's
actual mode-1 scan path and private-room occupancy rule.

## Verification

### Command-family slice
- `./venv/bin/python -m pytest -q tests/integration/test_do_equipment.py tests/integration/test_do_inventory.py tests/integration/test_do_where_command.py tests/test_player_info_commands.py tests/test_act_info_rom_parity.py`
- Result: `66 passed`

### Adjacent equipment band
- `./venv/bin/python -m pytest -q tests/integration/test_do_equipment.py tests/integration/test_equipment_system.py tests/integration/test_equipment_ac_calculations.py tests/test_player_equipment.py`
- Result: `88 passed, 1 skipped`

## Next step

Continue the `act_info.c` trust-rebuild on the remaining weak user-visible
surfaces, with `who` and `look` now the best next targets.
