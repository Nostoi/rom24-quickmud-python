# Session Summary — 2026-05-21 — `act_info.c` trust rebuild: `do_look`

## What landed

Continued the `act_info.c` trust-rebuild with `do_look`.

This slice found two real user-visible parity bugs on the basic room-look path.

## Real bugs fixed

### 1. `do_look` always showed exits even without `PLR_AUTOEXIT`

ROM only calls `do_exits("auto")` inside the `PLR_AUTOEXIT` branch.
Python was emitting an unconditional hand-built exits line, then appending the
ROM-style autoexit line on top when `PLR_AUTOEXIT` was set.

Fixed in:
- `/Users/markjedrzejk/dev/projects/rom24-quickmud-python/mud/world/look.py`

### 2. Room look prefixed contents and people with Python-only labels

ROM appends room contents and visible occupants directly through
`show_list_to_char` and `show_char_to_char`. Python was rendering:
- `Objects: ...`
- `Characters: ...`

Those labels are not ROM behavior.

Fixed in:
- `/Users/markjedrzejk/dev/projects/rom24-quickmud-python/mud/world/look.py`

## Test tightening

Added:
- `/Users/markjedrzejk/dev/projects/rom24-quickmud-python/tests/integration/test_do_look_command.py`

Coverage now includes:
- no exit line without `PLR_AUTOEXIT`
- one autoexit line with `PLR_AUTOEXIT`
- raw room-content line rendering
- raw visible-occupant line rendering

## Verification

- `./venv/bin/python -m pytest -q tests/integration/test_do_look_command.py`
- Result: `4 passed`

- broader look-adjacent band:
  - `tests/integration/test_do_look_command.py`
  - `tests/integration/test_do_examine_command.py`
  - `tests/test_world.py`
  - `tests/test_commands.py -k 'look or examine or exits or autoexit or sleeping'`
- Result: `19 passed, 27 deselected`

## Next step

`do_look` still has more surface area left than this first slice covered.
Next best follow-up is the dark-room / blindness / container-detail branches,
then the trust-rebuild can move from `act_info.c` to `nanny.c` / `save.c`.
