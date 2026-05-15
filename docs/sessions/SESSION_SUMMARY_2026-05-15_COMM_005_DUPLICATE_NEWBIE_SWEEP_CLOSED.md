# Session Summary — 2026-05-15 — COMM-005 duplicate-newbie sweep closed

## What changed

Closed `COMM-005` from `docs/parity/COMM_C_AUDIT.md`.

ROM `src/comm.c:1804-1825` rejects a new-character name when another non-`CON_PLAYING`
descriptor is already holding that same name. It closes those duplicate descriptors,
then wiznets `"Double newbie alert (%s)"` on `WIZ_LOGINS`.

QuickMUD did not implement that sweep. The async login path only did the syntactic,
clan-name, and mob-keyword checks.

## Implementation

### `mud/net/connection.py`

Added lightweight ROM-style descriptor tracking for live connections:

- `_descriptor_list()`
- `_register_descriptor(...)`
- `_unregister_descriptor(...)`
- `_set_descriptor_name(...)`
- `_mark_descriptor_playing(...)`

Added the actual parity closure:

- `_close_duplicate_newbie_descriptors(...)`

`_run_character_login(...)` now:

1. registers the connection in `descriptor_list`
2. stores the pending character name on the descriptor during `Name:` handling
3. after `is_valid_character_name(...)`, mirrors ROM's duplicate-newbie sweep
4. closes matching non-playing descriptors
5. broadcasts `Double newbie alert (<name>)` on `WIZ_LOGINS`
6. rejects the current name with `Illegal name, try another.`

Both `handle_connection(...)` and `handle_connection_with_stream(...)` now keep the
descriptor entry in sync and mark it `CON_PLAYING` after session creation.

## Tests

Added regression coverage:

- `tests/test_account_auth.py::test_new_character_name_rejects_duplicate_newbie_and_wiznets`

Verified with:

- `./venv/bin/python -m pytest -q tests/test_account_auth.py -k 'wrong_password_once or duplicate_newbie'`
- `./venv/bin/python -m pytest -q tests/integration/test_nanny_login_parity.py -k 'wrong_password or denied or login'`
- `./venv/bin/python -m pytest -q tests/test_wiznet.py -k 'login or site or prefix or broadcast'`
- `./venv/bin/python -m pytest -q tests/integration/test_act_wiz_command_parity.py -k 'disconnect or users or where'`

## Docs updated

- `docs/parity/COMM_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`

## Result

`comm.c` non-networking parity is now fully closed.
Only the intentional asyncio networking-architecture divergence remains out of scope.
