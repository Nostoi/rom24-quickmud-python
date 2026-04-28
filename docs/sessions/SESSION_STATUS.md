# Session Status — 2026-04-28 — `interp.c` 22/24 fixed (+1 deferred, +1 closed-deferred)

## Current State

- **Active audit**: `interp.c` (Phase 4 — only `INTERP-013` remains
  open, blocked on `ACT_OBJ_C` `do_wear` port).
- **Last completed**: INTERP-015 (`one_argument` Python port replacing
  `shlex.split`) and INTERP-016 (`tail_chain` verified empty in stock
  ROM, closed-deferred). Plus a test correction in
  `test_alias_parity.py` to assert ROM-faithful case-insensitive
  alias lookup.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-28_INTERP_ONE_ARGUMENT_AND_TAIL_CHAIN.md](SESSION_SUMMARY_2026-04-28_INTERP_ONE_ARGUMENT_AND_TAIL_CHAIN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.12 |
| Tests (interp_dispatcher suite) | 28 / 28 passing |
| Tests (interp_prefix_order suite) | 45 / 45 passing |
| Tests (test_alias_parity.py) | 14 / 14 passing |
| Tests (full integration + alias + help + comm sweep) | 1229 / 1229 passing, 10 skipped (~3 min) |
| ROM C files audited | 16 / 43 (no change — `interp.c` still ⚠️ Partial pending INTERP-013) |
| `interp.c` gaps closed | 22 / 24 fixed + 1 closed-deferred + 1 deferred-pending (92%+) |
| Active focus | `ACT_OBJ_C_AUDIT.md` — file `WEAR-001`/`WEAR-002` for the wield/hold pieces missing from `do_wear`, then collapse to satisfy `INTERP-013` |

## Recent Commits (this iteration)

- `22fa717` — `fix(parity): interp.c:INTERP-015 — port ROM one_argument; close INTERP-016`

## Next Intended Task

The remaining `interp.c` work blocks on `ACT_OBJ_C`:

1. **`ACT_OBJ_C` add-on gaps** in `docs/parity/ACT_OBJ_C_AUDIT.md`:
   - `WEAR-001` — port STR wield-weight check, weapon-skill flavor
     message, two-hand vs shield conflict from
     `mud/commands/equipment.py:do_wield` into `do_wear`.
   - `WEAR-002` — port HOLD auto-unequip behavior from ROM
     `wear_obj()` (`src/act_obj.c:1670-1678`) into `do_wear`; the
     current Python `do_hold` rejects with "already holding" instead
     of removing the existing item.
2. After `WEAR-001`/`WEAR-002` close, collapse `do_wield`/`do_hold`
   into aliases on `do_wear` to satisfy `INTERP-013`.

## Outstanding Cleanup (carried over)

- **RNG-isolation flake between integration and unit suites** —
  unchanged from prior sessions.
  `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  passes alone but fails after integration tests run because there's
  no session-scoped `rng_mm.seed_mm` autouse fixture in
  `tests/conftest.py`. Suggested fix:
  `fix(test): isolate rng_mm state across test suites`.
- **`tests/integration/test_character_advancement.py::test_kill_mob_grants_xp_integration`**
  — same RNG-ordering flake; passes alone, fails when run after the
  full integration sweep. Same root cause.
