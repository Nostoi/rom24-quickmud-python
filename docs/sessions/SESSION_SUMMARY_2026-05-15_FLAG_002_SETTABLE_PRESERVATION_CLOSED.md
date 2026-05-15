# Session Summary — 2026-05-15 — `FLAG-002` settable-bit preservation closed

## What landed

- Closed `FLAG-002` in `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/FLAGS_C_AUDIT.md`.
- Updated `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/remaining_rom.py:do_flag` to preserve ROM `settable=FALSE` rows across the `=` operator.
- Added regression coverage in `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_flag_command_parity.py`.

## ROM reference

- Preservation loop: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/flags.c:220`
- Table metadata: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/tables.c:82`, `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/tables.c:108`, `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/tables.c:271`

## Implementation details

- Added `_NON_SETTABLE_FLAGS_BY_FIELD` in `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/remaining_rom.py`.
- Encoded the exact `settable=FALSE` rows used by ROM for:
  - `act` → `npc`
  - `plr` → all rows except `permit`
  - `comm` → `noemote`, `noshout`, `notell`, `nochannels`, `snoop_proof`
- Changed `do_flag(... =...)` to initialize `new` with `old & preserve_mask` before applying requested bits.

## Tests

- Updated `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_flag_command_parity.py`:
  - corrected one stale expectation that contradicted ROM `settable=FALSE` semantics
  - added explicit regression coverage for preserved `plr` and `act` bits
- Verification:
  - `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_flag_command_parity.py`
  - `./venv/bin/python -m ruff check /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/remaining_rom.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_flag_command_parity.py`

## Status impact

- `flags.c` remains fully audited, now with no deferred gap.
- The tracker row `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` now records `flags.c / bit.c` as fully closed.

## Next candidates

- `COMM-005` in `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/COMM_C_AUDIT.md`
- `NANNY-010` in `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/NANNY_C_AUDIT.md`
