# Session Summary — 2026-05-13 — NANNY-009 title table port and default-title wiring

## What changed

- Closed `NANNY-009` by porting ROM `title_table` from `src/const.c:421-721` into `mud/models/titles.py`.
- Wired new-character creation to persist the ROM level-1 default title in `mud/account/account_service.py`.
- Wired `advance_level()` to reset the class title for the current level in `mud/advancement.py`, matching ROM `src/update.c`.
- Refactored `mud/commands/character.py::set_title()` to reuse the shared title-formatting helper.

## Root cause

- Python had the custom-title command and spacing helper, but it had never ported the ROM title data itself.
- That left two visible parity gaps:
  - new characters loaded with `pcdata.title == None` instead of `the <class title>`
  - level-ups preserved stale custom titles instead of restoring the ROM class title for the new level
- ROM uses the same `title_table[class][level][sex]` source for both the creation path (`nanny.c`) and level advancement (`update.c` / `do_advance`).

## Files touched

- `mud/models/titles.py`
- `mud/account/account_service.py`
- `mud/advancement.py`
- `mud/commands/character.py`
- `tests/test_advancement.py`
- `tests/integration/test_character_creation_runtime.py`
- `docs/parity/NANNY_C_AUDIT.md`
- `docs/parity/CONST_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`

## Verification

- Red/green checks:
  - `./venv/bin/python -m pytest -q tests/test_advancement.py::test_advance_level_resets_title_to_rom_default tests/integration/test_character_creation_runtime.py::test_new_character_gets_rom_default_title_on_load`
  - both failed before the implementation, then passed after
- Targeted affected surfaces:
  - `./venv/bin/python -m pytest -q tests/test_advancement.py tests/integration/test_character_creation_runtime.py tests/integration/test_nanny_login_parity.py tests/test_player_title_description.py tests/test_account_auth.py -q`
  - passed
- Lint:
  - `./venv/bin/ruff check mud/models/titles.py mud/account/account_service.py mud/advancement.py mud/commands/character.py tests/test_advancement.py tests/integration/test_character_creation_runtime.py`
  - passed
- Full suite:
  - `./venv/bin/python -m pytest -q --maxfail=1`
  - `4527 passed, 11 skipped in 645.82s (0:10:45)`

## Notes

- `nanny.c` now has only one remaining deferred item: `NANNY-010` (`CON_BREAK_CONNECT` full descriptor sweep), still deferred-by-design because Python’s `SESSIONS` map enforces the same invariant structurally.
- `const.c` now has one remaining deferred item: `CONST-007` (`weapon_table`), still reserved for the OLC cluster.
