# Session Status — 2026-04-27 — `interp.c` dispatcher hook cluster complete

## Current State

- **Active audit**: `interp.c` (Phase 4 — gap closure in progress;
  11 of 24 gaps FIXED; full social cluster, INTERP-001 trust drift,
  and the dispatcher-hook cluster (INTERP-002/003/007/008) all done).
- **Last completed**: INTERP-007, INTERP-008, INTERP-002, INTERP-003 —
  empty-input silent return, ROM punctuation aliases, snoop-by
  forwarding, wiznet `WIZ_SECURE` log-mirror verification.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-27_INTERP_DISPATCHER_HOOKS.md](SESSION_SUMMARY_2026-04-27_INTERP_DISPATCHER_HOOKS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.9 |
| Tests (interp_dispatcher suite) | 10 / 10 passing |
| Tests (interp_trust suite) | 50 / 50 passing |
| Tests (socials suite) | 31 / 31 passing |
| Tests (alias_parity suite) | 14 / 14 passing |
| ROM C files audited | 16 / 43 (no change — `interp.c` still ⚠️ Partial) |
| `interp.c` gaps closed | 11 / 24 (46%) |
| Active focus | `interp.c` — dispatcher hooks done; command-mapping cleanup (INTERP-009..014), prefix-order sweep (INTERP-017), and INTERP-024 (`do_commands`/`do_wizhelp` formatting) remain |

## Recent Commits (this session)

- `6146ea5` — `fix(parity): interp.c:INTERP-007 — empty input returns silently`
- `42dc0d1` — `fix(parity): interp.c:INTERP-008 — add ., ,, / punctuation aliases`
- `1ef8a10` — `fix(parity): interp.c:INTERP-002 — forward snoop logline to snooper`
- `b17ad93` — `test(parity): interp.c:INTERP-003 — verify wiznet WIZ_SECURE log mirror`

## Next Intended Task

The remaining `interp.c` work is correctness/cleanup only:

1. **INTERP-017** — prefix-match table-order divergence. Needs an
   empirical sweep test that walks every `cmd_table[]` prefix and
   confirms `resolve_command` returns the same first-match command
   ROM does.
2. **INTERP-009..014** — command-mapping cleanup: route `hit`, `take`,
   `junk`, `tap`, `go`, `wield`, `hold`, `:` to ROM's canonical
   handlers (`do_kill`, `do_get`, `do_sacrifice`, `do_enter`,
   `do_wear`, `do_immtalk`) rather than separate Python stubs. These
   are higher-impact because they may break tests that expect the
   current Python stubs.
3. **INTERP-024** — verify `do_commands`/`do_wizhelp` column format
   (12-char left-justified, 6 per line) and `LEVEL_HERO`
   mortal/immortal split.

## Outstanding Cleanup (carried over)

- **RNG-isolation flake between integration and unit suites** —
  unchanged from prior sessions.
  `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  passes alone but fails after integration tests run because there's
  no session-scoped `rng_mm.seed_mm` autouse fixture in
  `tests/conftest.py`. Suggested fix:
  `fix(test): isolate rng_mm state across test suites`.
