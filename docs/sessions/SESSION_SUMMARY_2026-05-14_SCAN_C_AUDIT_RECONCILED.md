# Session Summary — 2026-05-14 — scan.c audit reconciled

## Scope

The tracker still listed `scan.c` as missing and unaudited. That claim was checked
directly against ROM `src/scan.c`, the live Python implementation, and existing test
coverage.

## What was found

- `do_scan` already exists in `mud/commands/inspection.py`
- `scan` is already wired in `mud/commands/dispatcher.py`
- `spell_farsight` already delegates to `do_scan`
- Dedicated scan coverage already existed in:
  - `tests/test_scan_parity.py`
  - `tests/integration/test_scan_broadcasts.py`
  - `tests/test_commands.py`
  - `tests/test_spell_farsight_rom_parity.py`

The open tracker row was stale, not a real gameplay gap.

## Changes made

- Added `docs/parity/SCAN_C_AUDIT.md`
- Replaced the stale `scan.c` tracker row in
  `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Tightened permissive scan tests in `tests/test_scan_parity.py` to require ROM-faithful
  output instead of allowing invented fallback strings
- Updated `docs/sessions/SESSION_STATUS.md`

## Verification

- `./venv/bin/python -m pytest -q tests/test_scan_parity.py`
- `./venv/bin/python -m pytest -q tests/integration/test_scan_broadcasts.py`
- `./venv/bin/python -m pytest -q tests/test_commands.py -k 'scan or farsight'`

## Outcome

`scan.c` is now recorded accurately as audited and implemented. No production code change
was required.

## Next task

Return to `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` and pick the next open
non-deferred row that is still a real gap rather than stale tracker drift.
