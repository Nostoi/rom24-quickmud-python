# Session Status — 2026-05-21 — act_info trust-rebuild extended through `do_look` branch parity

## Current State

- **The `act_info.c` trust-rebuild is active and `do_look` has now been extended through the dark-room / blindness / `look in` branches.**
- Confirmed and fixed:
  - session `logon` refresh on ORM load
  - `score` title/race/class rendering
  - `score` player-race name mapping for human/pc-race ids
  - low-level AC wording in `score`
  - `whois` descriptor-path formatting, flag display, and switched-original output
  - `do_look` autoexit-only exits behavior
  - `do_look` raw room contents / occupant rendering
  - `do_look` dark-room visible-occupant formatting
  - `do_look` drink-container liquid-color wording
  - `do_look` closed-container `CONT_CLOSED` handling
  - `do_look` blind-gate message parity via `check_blind()`
- The completed create → reconnect path still persists correctly under the real WebSocket flow.
- **Pointer to latest summary**:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-21_ACT_INFO_TRUST_REBUILD_LOOK_BRANCHES.md`

## What changed in this sub-slice

- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/world/look.py`
- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/rom_api.py`
- Added stricter regressions in:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_do_look_command.py`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_rom_api.py`
- Updated `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ACT_INFO_C_AUDIT.md`

## Verification

- Focused `do_look` slice:
  - `./venv/bin/python -m pytest -q tests/integration/test_do_look_command.py`
  - `8 passed`
- Broader look/examine/helper band:
  - `./venv/bin/python -m pytest -q tests/integration/test_do_look_command.py tests/integration/test_do_examine_command.py tests/test_world.py tests/test_commands.py tests/test_rom_api.py -k 'look or examine or exits or autoexit or sleeping or check_blind'`
  - `28 passed, 39 deselected`

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.28 |
| `score` parity bug | **fixed** |
| `whois` ROM formatting bug | **fixed** |
| `do_equipment` slot-order bug | **fixed** |
| `do_where` private-room bug | **fixed** |
| `do_who` switched-session bug | **fixed** |
| `do_look` dark-room / blind / look-in branch gaps | **fixed** |
| WebSocket create → reconnect path | **green in test** |
| Current `do_look` verification slice | **28 passed, 39 deselected** |
| Last known full suite | **green (`4571 passed, 4 skipped`)** |

## Next Intended Task

1. Commit the current `do_look` branch-parity slice.
2. Only continue `do_look` if a concrete ROM/output mismatch is found in the remaining branches.
3. Otherwise move the trust-rebuild to `nanny.c` / `save.c` runtime-path re-audits.
4. Keep using the differential-testing design at `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`.
