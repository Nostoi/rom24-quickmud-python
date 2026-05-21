# Session Status — 2026-05-21 — act_info trust-rebuild extended through `equipment` / `inventory` / `where`

## Current State

- **The first trust-rebuild sub-slice inside `act_info.c` is now underway.**
- Confirmed and fixed:
  - session `logon` refresh on ORM load
  - `score` title/race/class rendering
  - `score` player-race name mapping for human/pc-race ids
  - low-level AC wording in `score`
  - `whois` descriptor-path formatting, flag display, and switched-original output
- The completed create → reconnect path still persists correctly under the real WebSocket flow.
- **Pointer to latest summary**:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-21_ACT_INFO_TRUST_REBUILD_EQUIPMENT_INVENTORY_WHERE.md`

## What changed in this sub-slice

- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/session.py`
- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/handler.py`
- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/models/character.py`
- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/info_extended.py`
- Added stricter regressions in:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_player_info_commands.py`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
- Updated `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ACT_INFO_C_AUDIT.md`
- Wrote the trust-rebuild re-audit plan:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/plans/2026-05-21-parity-trust-rebuild-reaudit.md`
- Wrote the differential-testing design spec:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`

## Verification

- Focused verification slice:
  - `./venv/bin/python -m pytest -q tests/test_player_info_commands.py tests/test_websocket_server.py tests/integration/test_character_creation_runtime.py tests/integration/test_db_canonical_round_trip.py tests/test_act_info_rom_parity.py`
  - `51 passed`
- Latest full-suite recertification after the score/login fixes:
  - `./venv/bin/python -m pytest -q --maxfail=1`
  - `4571 passed, 4 skipped`

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.22 |
| `score` parity bug | **fixed** |
| `whois` ROM formatting bug | **fixed** |
| `do_equipment` slot-order bug | **fixed** |
| `do_where` private-room bug | **fixed** |
| WebSocket create → reconnect path | **green in test** |
| Focused verification slice | **66 passed** |
| Full suite | **green (`4571 passed, 4 skipped`)** |

## Next Intended Task

1. Commit the second `act_info.c` trust-rebuild slice (`equipment` / `inventory` / `where`).
2. Continue `act_info.c` revalidation with the next user-visible weak-output surface:
   - `who`
   - `look`
3. Keep using the differential-testing design at `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`.
4. After the next `act_info.c` slice, move to `nanny.c` / `save.c` runtime-path re-audits.
