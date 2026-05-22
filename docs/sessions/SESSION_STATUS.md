# Session Status — 2026-05-21 — `nanny.c` trust-rebuild started on returning level-1 login flow

## Current State

- **The trust-rebuild has moved from `act_info.c` into `nanny.c` / `save.c` runtime-path verification.**
- Confirmed and fixed in this sub-slice:
  - returning level-1 characters no longer replay the one-time first-login
    school outfit flow on later logins
  - `_is_new_player()` now uses the persisted `newbie_help_seen` marker
    instead of the overly broad `played == 0` heuristic
- The new runtime-path regression proves a real WebSocket relogin no longer
  re-emits `"You have been equipped by Mota."` for an existing character.
- **Pointer to latest summary**:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-21_NANNY_TRUST_REBUILD_RETURNING_LEVEL1_LOGIN_FLOW.md`

## What changed in this sub-slice

- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/connection.py`
- Added stricter runtime-path regressions in:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_connection_motd.py`
- Updated `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/NANNY_C_AUDIT.md`

## Verification

- Focused WebSocket runtime-path slice:
  - `./venv/bin/python -m pytest -q tests/test_websocket_server.py`
  - `3 passed`
- Broader `nanny` / login runtime-path band:
  - `./venv/bin/python -m pytest -q tests/test_connection_motd.py tests/test_websocket_server.py tests/integration/test_nanny_login_parity.py tests/integration/test_character_creation_runtime.py -k 'login or reconnect or newbie or motd or title or score or persist'`
  - `24 passed, 12 deselected`

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.29 |
| Returning level-1 relogin outfit replay bug | **fixed** |
| WebSocket create → reconnect path | **green in test** |
| Current `nanny` runtime-path verification band | **24 passed, 12 deselected** |
| Last known full suite | **green (`4571 passed, 4 skipped`)** |

## Next Intended Task

1. Continue the `nanny.c` / `save.c` runtime-path trust rebuild.
2. Target the next real boundary mismatch in post-login observable state, starting with reconnect → first `score` / first room output.
3. Keep using the differential-testing design at `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`.
