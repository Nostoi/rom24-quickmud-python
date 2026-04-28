# Session Status — 2026-04-28 — `interp.c` 20/24 gaps closed

## Current State

- **Active audit**: `interp.c` (Phase 4 — gap closure;
  20 of 24 gaps closed).
- **Last completed**: INTERP-004/005/006 position/trust gates
  (`shout` min_trust=3, `murder` min_trust=5, `music`
  min_position=SLEEPING) plus `make_player` test fixture uplift to
  `LEVEL_HERO-1` so mortal-channel tests still pass.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-28_INTERP_POSITION_TRUST_GATES.md](SESSION_SUMMARY_2026-04-28_INTERP_POSITION_TRUST_GATES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.11 |
| Tests (interp_dispatcher suite) | 20 / 20 passing |
| Tests (interp_prefix_order suite) | 45 / 45 passing |
| Tests (test_communication.py) | 17 / 17 passing |
| Tests (full integration + alias + help + comm sweep) | all green after fixture fix |
| ROM C files audited | 16 / 43 (no change — `interp.c` still ⚠️ Partial) |
| `interp.c` gaps closed | 20 / 24 (83%) |
| Active focus | `interp.c` — INTERP-013 (blocked on ACT_OBJ_C wear-port), INTERP-015 (shlex/one_argument), INTERP-016 (defer-document) |

## Recent Commits (this iteration)

- `73d4261` — `fix(parity): interp.c:INTERP-004 — shout requires trust 3`
- `3058388` — `fix(parity): interp.c:INTERP-005 — murder requires trust 5`
- `1c755c7` — `fix(parity): interp.c:INTERP-006 — music min_position SLEEPING`
- `1ac6d92` — `test(parity): give make_player hero-level trust for shout/murder gates`

## Next Intended Task

The remaining `interp.c` work:

1. **INTERP-013** — port the missing wield/hold behavior into
   `do_wear` (STR check, weapon-skill flavor, two-hand conflict, HOLD
   auto-unequip) under new `WEAR-001`/`WEAR-002` gap IDs in
   `ACT_OBJ_C_AUDIT.md`, then collapse `do_wield`/`do_hold` into
   aliases on `do_wear`.
2. **INTERP-015** — replace `shlex.split` in `_split_command_and_args`
   with a ROM-faithful `one_argument` port (backslash semantics).
3. **INTERP-016** — document `tail_chain()` as a no-op extension
   hook; defer.

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
