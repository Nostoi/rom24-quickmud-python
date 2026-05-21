# Session Summary — 2026-05-21 — Score parity fix and trust-rebuild pivot

## What landed

- Fixed a real live ROM-parity bug on the `score` surface.
- Added stricter runtime-path and ROM-exact regressions for `score` and create→reconnect behavior.
- Downgraded unsupported “100% verified/certified” public language in `README.md`.
- Wrote a new trust-rebuild re-audit plan and a dedicated differential-testing design spec for the next agents.

## Root causes found

### 1. `score` output was not ROM-faithful

The live bug report was valid. QuickMUD was incorrectly:

- rendering integer race IDs instead of ROM race names
- rendering `Class: unknown` instead of the ROM class label
- dropping the ROM player title in some cases
- treating `logon=0` like Unix epoch during score/age display
- using a non-ROM low-level armor summary (`defenseless armored`) instead of ROM’s four AC lines

## Code changes

### Fixed

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/session.py`
  - `do_score()` now uses:
    - `pcdata.title`
    - ROM race/class helpers
    - ROM-style hour calculation
    - ROM AC wording/line structure
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/handler.py`
  - `get_age()` now handles session `logon` correctly and uses `c_div`
  - `race_name()` now resolves integer race IDs correctly via race-table index
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/models/character.py`
  - `from_orm()` now sets live-session `logon` to current time, matching ROM load semantics

## Test changes

### Added / strengthened

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_player_info_commands.py`
  - ROM title/race/class rendering
  - zero-logon age/hour sanity
  - ROM low-level AC wording
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_websocket_server.py`
  - complete create→disconnect→reconnect path
  - DB row persisted after completed creation
  - second login gets `Password:` instead of restarting creation

## Important finding on “character not persisting”

I did **not** reproduce a server-side “must recreate character every login” bug once the creation flow was completed end-to-end.

Verified behavior:

- full WebSocket creation persisted:
  - `level == 1`
  - `race == 1`
  - `ch_class == 0`
  - `title == " the Apprentice of Magic"`
- second connection prompted `Password:`

Interpretation:

- the persistence complaint is not currently proven as an engine bug
- the prior observed behavior may have come from:
  - an incomplete creation session
  - a client/server DB-path mismatch
  - or another environment-path issue outside the reproduced server path

## Verification

### Focused slice

- `./venv/bin/python -m pytest -q tests/test_player_info_commands.py tests/test_websocket_server.py tests/integration/test_character_creation_runtime.py tests/integration/test_db_canonical_round_trip.py tests/test_act_info_rom_parity.py`
- Result: `49 passed`

### Full suite

- `./venv/bin/python -m pytest -q --maxfail=1`
- Result: `4571 passed, 4 skipped`

## Documentation changes

### Public claims downgraded

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/README.md`
  - “100% verified/certified” language downgraded to revalidation-in-progress language

### Verification standard tightened

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/ROM_PARITY_VERIFICATION_GUIDE.md`
  - added confidence tiers
  - clarified that smoke tests and audit coverage are insufficient for parity claims
  - clarified runtime-path requirements for session/boundary surfaces

### New planning/spec artifacts

- Trust-rebuild re-audit plan:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/plans/2026-05-21-parity-trust-rebuild-reaudit.md`
- Differential-testing design:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`

## What the next agent should do

Start the parity trust-rebuild program, not generic parity hunting.

### Immediate first slice

1. Re-audit:
   - `src/act_info.c`
   - `src/nanny.c`
   - `src/save.c`
2. Use the differential-testing spec to choose comparison mode:
   - formula differential for pure logic
   - transcript differential for user-visible commands/prompts
   - scenario-state differential for stateful flows
3. Replace weak smoke assertions with ROM-exact output and runtime-path tests

### Critical rule

Do not restore “verified/certified” language until the stricter trust-rebuild slices are actually complete.
