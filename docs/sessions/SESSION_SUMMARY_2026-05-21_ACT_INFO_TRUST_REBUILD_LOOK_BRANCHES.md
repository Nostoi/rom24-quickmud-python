# Session Summary — 2026-05-21 — `act_info.c` trust rebuild: `do_look` dark-room, blind, and `look in` branches

## What landed

Continued the `act_info.c` trust-rebuild on the remaining high-risk `do_look`
branches after the first room-look slice.

This slice closed four real ROM-visible gaps:

1. **Dark-room formatting**
   - Python was still rendering a non-ROM `Characters:` label in dark rooms.
   - Fixed in:
     - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/world/look.py`

2. **Drink-container wording**
   - `look in <drink>` was omitting the ROM liquid color and spacing contract.
   - Fixed in:
     - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/world/look.py`

3. **Closed-container bit parity**
   - `look in <container>` was checking the wrong close bit instead of ROM
     `CONT_CLOSED = 4`.
   - Fixed in:
     - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/world/look.py`

4. **Blind-gate parity**
   - `check_blind()` was effectively a no-op for `do_look`, so blind characters
     could still see normal room output.
   - Fixed in:
     - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/rom_api.py`
     - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/world/look.py`

## Tests added / tightened

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_do_look_command.py`
  - dark-room visible occupants render as raw lines
  - drink containers use ROM liquid-color wording
  - closed containers obey ROM `CONT_CLOSED`
  - blind characters get the ROM blind message
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_rom_api.py`
  - `check_blind()` now has an explicit blind-character regression

## Verification

- `./venv/bin/python -m pytest -q tests/integration/test_do_look_command.py`
  - `8 passed`
- `./venv/bin/python -m pytest -q tests/integration/test_do_look_command.py tests/integration/test_do_examine_command.py tests/test_world.py tests/test_commands.py tests/test_rom_api.py -k 'look or examine or exits or autoexit or sleeping or check_blind'`
  - `28 passed, 39 deselected`

## Next step

`do_look` still has branch surface left, but the highest-risk user-visible gaps
in the dark-room / blindness / `look in` path are now covered.

Next best move:
1. finish any remaining dense `do_look` branches only if a concrete ROM/output
   mismatch is found (`look <direction>`, extra-descr precedence, numbered
   object descriptions), then
2. move the trust-rebuild to `nanny.c` / `save.c` runtime-path re-audits.
