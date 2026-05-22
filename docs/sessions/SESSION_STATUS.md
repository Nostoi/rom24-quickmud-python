# Session Status — 2026-05-21 — `nanny.c` / `save.c` trust-rebuild closed outfit and board runtime gaps

## Current State

- **The trust-rebuild is still focused on `nanny.c` / `save.c` runtime-path verification.**
- Confirmed and fixed in this sub-slice:
  - returning level-1 characters keep the school outfit across
    disconnect/reconnect
  - `from_orm()` now restores equipped items instead of silently dropping them
  - carry totals are recomputed after inventory/equipment load
  - login once again emits the ROM board summary after the initial auto-look
- The new runtime-path regressions prove both:
  - reconnect preserves the same visible carry state seen immediately after creation
  - login emits `do_board("")` output at the end of `CON_READ_MOTD`
- **Pointer to latest summary**:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-21_NANNY_SAVE_TRUST_REBUILD_OUTFIT_AND_BOARD_RUNTIME_PATHS.md`

## What changed in this sub-slice

- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/models/character.py`
- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/connection.py`
- Added stricter regressions in:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_inv008_persistence_coherence.py`
- Updated:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/NANNY_C_AUDIT.md`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/SAVE_C_AUDIT.md`

## Verification

- Targeted runtime regressions:
  - `./venv/bin/python -m pytest -q tests/test_websocket_server.py::test_websocket_login_emits_board_summary_after_initial_look tests/test_websocket_server.py::test_websocket_reconnect_preserves_school_outfit_state tests/integration/test_inv008_persistence_coherence.py::test_inv008_equipment_and_carry_state_survive_round_trip`
  - `3 passed`
- Broader `nanny` / `save` / board runtime band:
  - `./venv/bin/python -m pytest -q tests/test_websocket_server.py tests/test_connection_motd.py tests/integration/test_nanny_login_parity.py tests/integration/test_character_creation_runtime.py tests/integration/test_inv008_persistence_coherence.py tests/integration/test_db_canonical_round_trip.py tests/test_boards.py tests/integration/test_boards_rom_parity.py -k 'login or reconnect or newbie or motd or title or score or persist or round_trip or creation or equipment or inventory or board or unread'`
  - `87 passed`

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.30 |
| Returning level-1 relogin outfit replay bug | **fixed** |
| Reconnect outfit persistence bug | **fixed** |
| Post-login board summary omission | **fixed** |
| Current `nanny` / `save` runtime-path verification band | **87 passed** |
| Last known full suite | **green (`4592 passed, 4 skipped`)** |

## Next Intended Task

1. Continue the `nanny.c` / `save.c` trust rebuild.
2. Target reconnect → prompt ordering / any remaining room-output drift.
3. Keep using the differential-testing design at `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`.
