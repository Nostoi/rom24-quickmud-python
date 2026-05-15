# Session Summary — 2026-05-14 — CONST-007 weapon_table centralized

## Scope

`CONST-007` was the last open item in `const.c`: Python still lacked the ROM
canonical `weapon_table[]`, and several consumers relied on local duplicate
subsets instead.

## What changed

- Added `mud/models/weapon_table.py` as the ROM-faithful shared table
- Repointed combat skill lookup to the shared table
- Repointed creation-time weapon-name → school-vnum lookup to the shared table
- Repointed load-time chosen-weapon skill seeding to the shared table
- Updated `handler.weapon_name()` to read through the canonical mapping

## Behavioral impact

The duplicated subset mappings previously hid a real parity miss: only three
school weapons seeded learned skill on load. All eight ROM school weapons now
seed through the canonical table, including `staff -> spear`.

## Verification

- `./venv/bin/python -m pytest -q tests/test_weapon_table_parity.py`
- `./venv/bin/python -m pytest -q tests/test_weapon_table_parity.py tests/integration/test_nanny_login_parity.py tests/test_nanny_rom_parity.py tests/integration/test_do_equipment.py -k 'weapon or equipment or chosen_weapon_skill'`
- `./venv/bin/python -m ruff check mud/models/weapon_table.py mud/account/account_service.py tests/test_weapon_table_parity.py`

## Docs updated

- `docs/parity/CONST_C_AUDIT.md`
- `docs/parity/NANNY_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/parity/OLC_C_AUDIT.md`
- `docs/sessions/SESSION_STATUS.md`

## Outcome

`CONST-007` is closed. `const.c` is now fully audited with no remaining
deferred `weapon_table` item.
