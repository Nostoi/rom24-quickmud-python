# Session Summary — 2026-04-28 — `interp.c` position/trust gates

## Scope

Continuation from yesterday's `interp.c` work (release 2.6.10 closed
seven gaps including the prefix-order sweep). This loop iteration
closed the three small position/trust-gate gaps that were the next
items in `SESSION_STATUS.md` Next Steps — `INTERP-004`/`-005`/`-006`.
Each is a one-line `Command(...)` parameter change.

After the dispatcher edits the regression sweep surfaced two
test-side bugs in `tests/test_communication.py` whose fixture created
level-0 characters and asserted Python's old too-permissive shout
behavior. Per AGENTS.md ("a test asserting a behavior that contradicts
ROM C is a bug in the test"), the fixture was raised to `LEVEL_HERO-1`
so actors pass mortal-only trust gates.

## Outcomes

### `INTERP-004` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:278`
- **ROM C**: `src/interp.c:200` (`{"shout", do_shout, POS_RESTING, 3, ...}`)
- **Gap**: `shout` had no `min_trust` (defaulted to 0). ROM requires 3.
- **Fix**: `min_trust=3` added to the `shout` Command.
- **Tests**: 1 (`test_interp_004_shout_requires_trust_3`).
- **Commit**: `73d4261`.

### `INTERP-005` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:312`
- **ROM C**: `src/interp.c:247` (`{"murder", do_murder, POS_FIGHTING, 5, ...}`)
- **Gap**: `murder` had no `min_trust`. ROM requires 5.
- **Fix**: `min_trust=5` added to the `murder` Command.
- **Tests**: 1 (`test_interp_005_murder_requires_trust_5`).
- **Commit**: `3058388`.

### `INTERP-006` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:289`
- **ROM C**: `src/interp.c:93` (`{"music", do_music, POS_SLEEPING, 0, ...}`)
- **Gap**: `music` `min_position=Position.RESTING`. ROM allows it
  while sleeping.
- **Fix**: `min_position=Position.SLEEPING`.
- **Tests**: 1 (`test_interp_006_music_min_position_sleeping`).
- **Commit**: `1c755c7`.

### Test fixture follow-up — `make_player` trust uplift

- **File**: `tests/test_communication.py:22-30`.
- **Reason**: Two pre-existing tests (`test_shout_respects_mute_and_ban`,
  `test_shout_and_tell_respect_comm_flags`) created characters at
  level 0 and expected `shout` to dispatch — incorrect after
  INTERP-004 set ROM's `min_trust=3`.
- **Fix**: `make_player` now sets `char.level = LEVEL_HERO - 1` so
  test mortals satisfy normal mortal-only trust gates without
  crossing into immortal commands.
- **Commit**: `1ac6d92`.

## Files Modified

- `mud/commands/dispatcher.py` — three `Command(...)` parameter
  changes (shout `min_trust`, murder `min_trust`, music
  `min_position`).
- `tests/integration/test_interp_dispatcher.py` — added 3 trust/
  position gate tests.
- `tests/test_communication.py` — `make_player` raises actor level
  to `LEVEL_HERO - 1`; added `LEVEL_HERO` to imports.
- `docs/parity/INTERP_C_AUDIT.md` — flipped rows: INTERP-004,
  INTERP-005, INTERP-006 → ✅ FIXED.
- `CHANGELOG.md` — added `[2.6.11]` section.
- `pyproject.toml` — `2.6.10` → `2.6.11`.

## Recent Commits (this iteration)

- `73d4261` — `fix(parity): interp.c:INTERP-004 — shout requires trust 3`
- `3058388` — `fix(parity): interp.c:INTERP-005 — murder requires trust 5`
- `1c755c7` — `fix(parity): interp.c:INTERP-006 — music min_position SLEEPING`
- `1ac6d92` — `test(parity): give make_player hero-level trust for shout/murder gates`

## Test Status

- `pytest tests/integration tests/test_alias_parity tests/test_help_system tests/test_communication`
  → **all green** after the fixture uplift (see `1ac6d92`). Pre-fix
  regression sweep showed two `test_communication` failures (now
  fixed) plus the long-standing `test_kill_mob_grants_xp_integration`
  ordering flake (passes alone, unrelated to this work).
- New tests: 3 cases in `test_interp_dispatcher.py`
  (`test_interp_004/005/006`).

## Audit Progress

- `interp.c`: **20 / 24 gaps closed** (83%, up from 17/24=71%).
  Tracker row stays ⚠️ Partial — 4 gaps remain:
  - `INTERP-013` (deferred — needs ACT_OBJ_C wield/hold port first)
  - `INTERP-015` (`shlex.split` → ROM `one_argument` port; minor)
  - `INTERP-016` (`tail_chain()` no-op hook; documentation defer)
  - `INTERP-022` (already FIXED in v2.6.5; row says ✅)
- ROM C files audited overall: **16 / 43**.

## Next Steps

1. **`INTERP-013`** — file new gaps in `ACT_OBJ_C_AUDIT.md`
   (`WEAR-001` STR/skill/two-hand checks, `WEAR-002` HOLD
   auto-unequip), close those, then collapse `do_wield`/`do_hold`
   into aliases on `do_wear` per ROM cmd_table semantics.
2. **`INTERP-015`** — port a ROM-faithful `one_argument` to replace
   `shlex.split` in `_split_command_and_args` so backslash and
   unbalanced-quote semantics match.
3. **`INTERP-016`** — document `tail_chain()` as a no-op extension
   hook; close-defer.
4. **Pre-existing RNG-isolation flake** — add session-scoped
   `rng_mm.seed_mm` autouse fixture to `tests/conftest.py`.
