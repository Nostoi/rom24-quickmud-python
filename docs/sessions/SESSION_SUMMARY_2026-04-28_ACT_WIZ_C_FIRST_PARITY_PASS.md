# Session Summary — 2026-04-28 — `act_wiz.c` first parity pass

## What landed

- Started the `act_wiz.c` file-level audit and wrote `docs/parity/ACT_WIZ_C_AUDIT.md`.
- Closed `WIZ-001`: owner/private-room admin movement now mirrors ROM for `goto`, `at`, and `transfer`.
- Closed `WIZ-002`: `violate` now uses ROM `find_location()` semantics and rejects public rooms with the ROM `use goto` hint.
- Closed `WIZ-003`: `protect` now uses ROM lookup/messages and toggles the real `CommFlag.SNOOP_PROOF` bit.
- Closed `WIZ-004`: `snoop` now blocks correctly on canonical `CommFlag.SNOOP_PROOF`.

## Files changed

- `mud/commands/imm_commands.py`
- `mud/commands/imm_admin.py`
- `mud/commands/imm_server.py`
- `tests/integration/test_act_wiz_command_parity.py`
- `docs/parity/ACT_WIZ_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`
- `CHANGELOG.md`

## Verification

- `pytest tests/integration/test_act_wiz_command_parity.py -q` → `4 passed`
- `ruff check mud/commands/imm_commands.py mud/commands/imm_admin.py mud/commands/imm_server.py tests/integration/test_act_wiz_command_parity.py` → clean

## Open work

- `WIZ-005`: full ROM `stat` family (`do_stat`, `do_rstat`, `do_ostat`, `do_mstat`)
- `WIZ-006`: ROM `do_log`
- `WIZ-007`: ROM `do_force`
- Remaining echo/punishment/load/server-control commands still need line-by-line verification

## Next task

Stay on `act_wiz.c`. The next high-value slice is the `stat` family because the current Python command only provides a simplified wrapper and the ROM detailed admin views are still missing.
