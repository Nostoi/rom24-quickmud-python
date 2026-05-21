# Session Summary — 2026-05-21 — `act_info.c` trust rebuild: `score` + `whois`

## What landed

- Continued the trust-rebuild re-audit inside `act_info.c`.
- Tightened `score` and `whois` from smoke coverage toward ROM-exact output coverage.
- Fixed one additional real `score` bug and one real `whois` bug exposed by stricter assertions.

## Real bugs fixed

### 1. `score` still mapped player race id `0` incorrectly

QuickMUD stores playable race ids using the PC-race ordering (`human == 0`,
`elf == 1`, ...), but the `score` path was still using the base `race_table`
lookup semantics. That meant a human player could render as `unique`.

Fixed in:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/handler.py`

Result:
- `score` now resolves player-visible race names through `PC_RACE_TABLE` for the
  player-facing path.

### 2. `whois` formatting was not actually ROM-faithful

The old implementation used:
- ad hoc class formatting (`ADV` fallback)
- raw integer race rendering in some cases
- hardcoded flag bits
- no switched-descriptor `original` handling
- no ROM-style descriptor `CON_PLAYING` filtering

Fixed in:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/info_extended.py`

Result:
- `whois` now mirrors ROM-style output more closely on the descriptor path:
  - correct race `who_name`
  - correct class / immortal rank labels
  - proper AFK / KILLER / THIEF display using enums
  - switched-descriptor `original` preference

## Test tightening

### Strengthened `score` coverage

Updated:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_player_info_commands.py`

New stronger assertions now cover:
- exact `score` opening line for titled characters
- exact race / sex / class line for player-visible output
- exact low-level AC wording
- zero-logon sanity (no Unix-epoch age bug)

### Added exact `whois` descriptor-path coverage

Updated:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_player_info_commands.py`

New exact assertions now cover:
- ROM-style descriptor-path formatting with race / class / title / flags
- switched-descriptor `original` output

## Verification

### Focused `player_info` slice

- `./venv/bin/python -m pytest -q tests/test_player_info_commands.py`
- Result: `25 passed`

### Focused trust-rebuild band

- `./venv/bin/python -m pytest -q tests/test_player_info_commands.py tests/test_websocket_server.py tests/integration/test_character_creation_runtime.py tests/integration/test_db_canonical_round_trip.py tests/test_act_info_rom_parity.py`
- Result: `51 passed`

## Documentation changes

Updated:
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ACT_INFO_C_AUDIT.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`

The `ACT_INFO_C_AUDIT.md` top matter now explicitly records that the legacy
“100% complete” claim was structural and that observable-behavior trust rebuild
is in progress.

## Next step

Continue the `act_info.c` trust-rebuild on the next weak user-visible surfaces:

1. `where`
2. `equipment`
3. `inventory`

After that, move to `nanny.c` / `save.c` runtime-path revalidation.
