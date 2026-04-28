# Session Status — 2026-04-27 — `interp.c` 17/24 gaps closed

## Current State

- **Active audit**: `interp.c` (Phase 4 — gap closure;
  17 of 24 gaps closed; remaining work is correctness-only).
- **Last completed**: INTERP-009/010/011/012/014 command-mapping
  cleanup (alias collapse), INTERP-024 column-padding fix, and
  INTERP-017 prefix-order sweep (Python's prefix scan now mirrors
  ROM `cmd_table[]` declaration order).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-27_INTERP_COMMAND_MAPPING_AND_PREFIX.md](SESSION_SUMMARY_2026-04-27_INTERP_COMMAND_MAPPING_AND_PREFIX.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.10 |
| Tests (interp_dispatcher suite) | 17 / 17 passing |
| Tests (interp_prefix_order suite) | 45 / 45 passing |
| Tests (full integration + alias + help sweep) | 1202 / 1202 passing, 10 skipped (75.8s) |
| ROM C files audited | 16 / 43 (no change — `interp.c` still ⚠️ Partial) |
| `interp.c` gaps closed | 17 / 24 (71%) |
| Active focus | `interp.c` — `INTERP-004`/`-005`/`-006` position/trust gates + `INTERP-013` (deferred until `do_wear` ports the missing wield/hold logic) + `INTERP-015` shlex/one_argument port |

## Recent Commits (this session)

- `64c4adf` — `fix(parity): interp.c:INTERP-009 — route 'hit' to do_kill`
- `97fdec1` — `fix(parity): interp.c:INTERP-010 — route 'take' to do_get`
- `324bd1d` — `fix(parity): interp.c:INTERP-011 — route 'junk'/'tap' to do_sacrifice`
- `5db5f00` — `fix(parity): interp.c:INTERP-012 — route 'go' to do_enter`
- `e1fd782` — `fix(parity): interp.c:INTERP-014 — route ':' to do_immtalk`
- `bc707ee` — `fix(parity): interp.c:INTERP-024 — preserve 12-char column padding`
- `69e5cab` — `fix(parity): interp.c:INTERP-017 — prefix scan walks ROM cmd_table order`

## Next Intended Task

The remaining `interp.c` work is correctness-only:

1. **INTERP-004/-005/-006** — small position/trust-gate fixes:
   `shout` (ROM `min_trust=3`), `murder` (ROM `min_trust=5`),
   `music` (`min_position=POS_SLEEPING` not `RESTING`).
2. **INTERP-013** — port missing wield/hold behavior into `do_wear`
   (STR check, weapon-skill flavor, two-hand conflict, HOLD
   auto-unequip), then collapse `do_wield`/`do_hold` into aliases.
   Track new gap IDs in `ACT_OBJ_C_AUDIT.md`.
3. **INTERP-015** — replace `shlex.split` in `_split_command_and_args`
   with a ROM-faithful `one_argument` port (backslash semantics).
4. **INTERP-016** — document `tail_chain()` as a no-op extension
   hook; defer.

## Outstanding Cleanup (carried over)

- **RNG-isolation flake between integration and unit suites** —
  unchanged from prior sessions.
  `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  passes alone but fails after integration tests run because there's
  no session-scoped `rng_mm.seed_mm` autouse fixture in
  `tests/conftest.py`. Suggested fix:
  `fix(test): isolate rng_mm state across test suites`.
