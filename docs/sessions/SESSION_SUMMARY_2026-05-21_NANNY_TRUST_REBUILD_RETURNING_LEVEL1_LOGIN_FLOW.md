# Session Summary — 2026-05-21 — `nanny.c` trust rebuild: returning level-1 login flow

## What landed

Started the `nanny.c` / `save.c` runtime-path trust rebuild and immediately
found a real live-login parity bug on the WebSocket path.

### Real bug fixed

Returning level-1 characters were being reclassified as "new players" on later
logins if their `played` time was still zero, which caused the runtime path to
replay the one-time first-login school outfit flow.

Observable symptom:
- reconnect/login could emit `"You have been equipped by Mota."` again for an
  existing level-1 character

Root cause:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/connection.py`
  used `_is_new_player(level <= 1 and played == 0)` as the outfit/newbie gate
- that is too broad for QuickMUD's persisted level-1 characters

Fix:
- `_is_new_player()` now uses the persisted `newbie_help_seen` flag as the
  durable one-time first-login marker for player characters

## Files changed

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/connection.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_connection_motd.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/NANNY_C_AUDIT.md`

## Tests added / tightened

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
  - real WebSocket relogin no longer replays `"equipped by Mota"` on a
    returning level-1 character
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_connection_motd.py`
  - `_is_new_player()` now has a direct contract test proving
    `newbie_help_seen=True` suppresses first-login classification

## Verification

- `./venv/bin/python -m pytest -q tests/test_websocket_server.py`
  - `3 passed`
- `./venv/bin/python -m pytest -q tests/test_connection_motd.py tests/test_websocket_server.py tests/integration/test_nanny_login_parity.py tests/integration/test_character_creation_runtime.py -k 'login or reconnect or newbie or motd or title or score or persist'`
  - `24 passed, 12 deselected`

## Next step

Continue the `nanny.c` / `save.c` runtime-path trust rebuild, focusing on the
first post-login observable surfaces:

1. exact post-login `score` / room-output state after reconnect
2. save/load boundary assertions that still rely on helper-path tests instead
   of real server-path verification
