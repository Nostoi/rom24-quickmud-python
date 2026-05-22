# Session Status — 2026-05-21 — `nanny.c` trust-rebuild closed welcome-line and forced-reconnect gaps

## Current State

- **The trust-rebuild is still focused on `nanny.c` / `save.c` runtime-path verification.**
- Confirmed and fixed in this sub-slice:
  - normal login now emits the ROM `Welcome to ROM 2.4.  Please don't feed the mobiles!` line
  - forced reconnects no longer run the normal welcome/look/board tail
  - the earlier outfit persistence and board-summary fixes remain green under full-suite recertification
- The new runtime-path regressions prove both:
  - normal login includes the ROM welcome line before entering play
  - forced reconnect takeover now follows the reconnect-specific path instead of the normal login tail
- **Pointer to latest summary**:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-21_NANNY_TRUST_REBUILD_WELCOME_LINE_AND_FORCED_RECONNECT_SPLIT.md`

## What changed in this sub-slice

- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/connection.py`
- Added stricter regressions in:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
- Updated:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/NANNY_C_AUDIT.md`

## Verification

- Targeted runtime regressions:
  - `./venv/bin/python -m pytest -q tests/test_telnet_server.py::test_telnet_break_connect_prompts_and_reconnects tests/test_websocket_server.py::test_websocket_login_emits_rom_welcome_line_on_entering_game tests/test_websocket_server.py::test_websocket_login_emits_board_summary_after_initial_look tests/test_websocket_server.py::test_websocket_reconnect_preserves_school_outfit_state`
  - `4 passed`
- Broader login/runtime band:
  - `./venv/bin/python -m pytest -q tests/test_websocket_server.py tests/test_connection_motd.py tests/test_telnet_server.py tests/integration/test_nanny_login_parity.py tests/integration/test_character_creation_runtime.py tests/integration/test_inv008_persistence_coherence.py tests/integration/test_db_canonical_round_trip.py tests/test_boards.py tests/integration/test_boards_rom_parity.py -k 'login or reconnect or newbie or motd or title or score or persist or round_trip or creation or equipment or inventory or board or unread or welcome or break_connect'`
  - `89 passed, 14 deselected`
- Full suite:
  - `./venv/bin/python -m pytest -q --maxfail=1`
  - `4593 passed, 4 skipped`

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.31 |
| Returning level-1 relogin outfit replay bug | **fixed** |
| Reconnect outfit persistence bug | **fixed** |
| Post-login board summary omission | **fixed** |
| Missing normal-login welcome line | **fixed** |
| Forced reconnect using normal login tail | **fixed** |
| Current login/runtime verification band | **89 passed, 14 deselected** |
| Last known full suite | **green (`4593 passed, 4 skipped`)** |

## Next Intended Task

1. Continue the `nanny.c` / `save.c` trust rebuild.
2. Compare remaining normal-login transcript ordering against ROM more exactly.
3. Keep using the differential-testing design at `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`.
