# Session Status — 2026-05-21 — score parity bug fixed, trust-rebuild re-audit queued

## Current State

- **A real ROM-parity bug was found on the live `score` surface after earlier “100% verified” claims.**
- Fixed:
  - session `logon` refresh on ORM load
  - `score` title/race/class rendering
  - low-level AC wording in `score`
  - integer race-name lookup
- The completed create → reconnect path currently persists correctly under the real WebSocket flow.
- **Pointer to latest summary**:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-21_SCORE_PARITY_FIX_AND_TRUST_REBUILD_PIVOT.md`

## What changed in this investigation

- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/session.py`
- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/handler.py`
- Fixed `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/models/character.py`
- Added stricter regressions in:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_player_info_commands.py`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
- Wrote the trust-rebuild re-audit plan:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/plans/2026-05-21-parity-trust-rebuild-reaudit.md`
- Wrote the differential-testing design spec:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`

## Verification

- Focused verification slice:
  - `./venv/bin/python -m pytest -q tests/test_player_info_commands.py tests/test_websocket_server.py tests/integration/test_character_creation_runtime.py tests/integration/test_db_canonical_round_trip.py tests/test_act_info_rom_parity.py`
  - `49 passed`
- Latest full-suite recertification after the score/login fixes:
  - `./venv/bin/python -m pytest -q --maxfail=1`
  - `4571 passed, 4 skipped`

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.22 |
| Score parity bug | **fixed** |
| WebSocket create → reconnect path | **green in test** |
| Focused verification slice | **49 passed** |
| Full suite | **green (`4571 passed, 4 skipped`)** |

## Next Intended Task

1. Commit the score/login/session fix slice.
2. Execute the trust-rebuild plan at `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/plans/2026-05-21-parity-trust-rebuild-reaudit.md`.
3. Use the differential-testing design at `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md` to choose the right comparison mode per surface.
4. Start with `act_info.c`, `nanny.c`, and `save.c` re-audits using ROM-exact output and runtime-path assertions, not smoke coverage.
