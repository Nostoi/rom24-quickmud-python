# Session Summary — 2026-05-15 — NANNY-010 full break-connect descriptor sweep

## What landed

- Closed `NANNY-010` in `mud/net/connection.py` by adding `_close_duplicate_reconnect_descriptors(...)`, mirroring ROM `src/nanny.c:307-352`.
- The reconnect path now sweeps the full lightweight `descriptor_list`, matching by `descriptor.original.name` for switched immortals and `descriptor.character.name` otherwise.
- Preserved the canonical takeover flow by excluding the primary active session from the pre-close sweep and leaving it to `_disconnect_session(...)`. That keeps the old-socket takeover notice intact.
- Updated `mud/commands/imm_admin.py` so `do_switch` / `do_return` keep the lightweight ROM descriptor's `original` field synchronized with the session state.

## Tests

- Added `tests/test_account_auth.py::test_break_connect_closes_all_matching_descriptors`
- Verified `tests/test_telnet_server.py::test_telnet_break_connect_prompts_and_reconnects`
- Re-ran focused reconnect coverage:
  - `./venv/bin/python -m pytest -q tests/test_account_auth.py -k 'duplicate_newbie or break_connect_closes_all_matching_descriptors or reconnect' tests/integration/test_act_wiz_command_parity.py -k 'switch or return' tests/integration/test_nanny_login_parity.py -k 'login or reconnect'`
  - `25 passed, 154 deselected`

## Files touched

- `mud/net/connection.py`
- `mud/commands/imm_admin.py`
- `tests/test_account_auth.py`
- `docs/parity/NANNY_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`

## Result

- `nanny.c` is now fully reconciled in the parity tracker.
- No open non-deferred `nanny.c` gap remains.
