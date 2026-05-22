# Session Summary — 2026-05-21 — `nanny.c` trust rebuild: welcome line and forced reconnect split

## What landed

Continued the `nanny.c` trust rebuild on the live login path and closed the
next two `CON_READ_MOTD` / reconnect runtime mismatches.

### Real bug 1 fixed — normal login skipped the ROM welcome line

Observable symptom:
- after creation/login, QuickMUD went straight from outfit/MOTD/newbie output
  to room look and board summary
- ROM always writes `Welcome to ROM 2.4.  Please don't feed the mobiles!`
  when play actually begins

Fix:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/connection.py`
  now sends the ROM welcome line on the normal login path before the rest of
  the `CON_READ_MOTD` tail

### Real bug 2 fixed — forced reconnects were running the normal login tail

Observable symptom:
- duplicate-session takeover reconnects were being pushed through the same
  welcome/look/board tail as a normal login
- full-suite telnet coverage exposed the sequencing drift

ROM reference:
- `src/comm.c:1836-1873` `check_reconnect(..., TRUE)` sends the reconnect
  message, room act, wiznet, and optional note reminder, then returns to play
  without running the normal `CON_READ_MOTD` look/board tail

Fix:
- forced reconnects now skip the normal welcome/look/board path
- normal logins still run welcome + look + board

## Files changed

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/connection.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/NANNY_C_AUDIT.md`

## Tests added / tightened

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
  - `test_websocket_login_emits_rom_welcome_line_on_entering_game`

## Verification

- targeted runtime regressions:
  - `./venv/bin/python -m pytest -q tests/test_telnet_server.py::test_telnet_break_connect_prompts_and_reconnects tests/test_websocket_server.py::test_websocket_login_emits_rom_welcome_line_on_entering_game tests/test_websocket_server.py::test_websocket_login_emits_board_summary_after_initial_look tests/test_websocket_server.py::test_websocket_reconnect_preserves_school_outfit_state`
  - `4 passed`
- broader login/runtime band:
  - `./venv/bin/python -m pytest -q tests/test_websocket_server.py tests/test_connection_motd.py tests/test_telnet_server.py tests/integration/test_nanny_login_parity.py tests/integration/test_character_creation_runtime.py tests/integration/test_inv008_persistence_coherence.py tests/integration/test_db_canonical_round_trip.py tests/test_boards.py tests/integration/test_boards_rom_parity.py -k 'login or reconnect or newbie or motd or title or score or persist or round_trip or creation or equipment or inventory or board or unread or welcome or break_connect'`
  - `89 passed, 14 deselected`
- full suite:
  - `./venv/bin/python -m pytest -q --maxfail=1`
  - `4593 passed, 4 skipped`

## Next step

Continue the trust rebuild on the next post-login/session-boundary surface:

1. compare remaining normal-login transcript ordering against ROM more exactly
2. continue `save.c` runtime-path revalidation where helper-path coverage still
   exceeds real server-path evidence
