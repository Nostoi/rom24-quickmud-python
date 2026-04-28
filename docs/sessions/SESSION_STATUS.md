# Session Status — 2026-04-28 — `interp.c` 100% closed (24/24 + 1 closed-deferred)

## Current State

- **Active audit**: none — `interp.c` just closed.
- **Last completed**: `WEAR-010` (do_wear dispatches weapons),
  `WEAR-011` (do_hold auto-replaces), `INTERP-013` (collapse
  `do_wield`/`do_hold` to aliases on `do_wear`).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-28_WEAR_010_011_AND_INTERP_013_COLLAPSE.md](SESSION_SUMMARY_2026-04-28_WEAR_010_011_AND_INTERP_013_COLLAPSE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.13 |
| Tests (integration + alias + help + comm sweep) | 1233 / 1233 passing, 10 skipped (~4:35) |
| Tests (interp_dispatcher suite) | 29 / 29 passing |
| Tests (interp_prefix_order suite) | 45 / 45 passing |
| Tests (equipment suites) | 70 / 70 passing |
| ROM C files audited | 16 / 43 — `interp.c` flips to ✅ AUDITED |
| `interp.c` gaps closed | 24 / 24 fixed + 1 closed-deferred (100%) |
| Active focus | open — pick next P0/P1 from `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` |

## Recent Commits (this iteration)

- `66a17f1` — `fix(parity): act_obj.c:WEAR-010 — do_wear dispatches weapons to wield branch`
- `7aba8a5` — `fix(parity): act_obj.c:WEAR-011 — do_hold auto-replaces existing held item`
- *(release commit pending in this handoff: INTERP-013 collapse + 2.6.13)*

## Next Intended Task

Pick the next P0/P1 file from
`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` and run `/rom-parity-audit`
on it.

## Outstanding Cleanup (carried over)

- **RNG-isolation flake between integration and unit suites** —
  unchanged from prior sessions.
  `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  and
  `tests/integration/test_character_advancement.py::test_kill_mob_grants_xp_integration`
  pass alone, fail after integration tests run because there's no
  session-scoped `rng_mm.seed_mm` autouse fixture in
  `tests/conftest.py`. Suggested fix:
  `fix(test): isolate rng_mm state across test suites`.
