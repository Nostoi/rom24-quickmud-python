# Session Status — 2026-04-27 — `interp.c` INTERP-001 trust sweep complete

## Current State

- **Active audit**: `interp.c` (Phase 4 — gap closure in progress;
  7 of 24 gaps FIXED; full social cluster + INTERP-001 trust drift
  done).
- **Last completed**: INTERP-001 — 43 immortal commands raised to
  ROM `cmd_table[]` trust tiers (ML, L1..L7). Security drift closed.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-27_INTERP_001_TRUST_SWEEP.md](SESSION_SUMMARY_2026-04-27_INTERP_001_TRUST_SWEEP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.8 |
| Tests (interp_trust suite) | 50 / 50 passing |
| Tests (socials suite) | 31 / 31 passing |
| ROM C files audited | 16 / 43 (no change — `interp.c` still ⚠️ Partial) |
| `interp.c` gaps closed | 7 / 24 (29%) |
| Active focus | `interp.c` — security drift closed; dispatcher hooks (INTERP-002/003/007/008/017), command-mapping cleanup (INTERP-009..014), and INTERP-024 (`do_commands`/`do_wizhelp` formatting) remain |

## Recent Commits (this session)

- `548098d` — `fix(parity): interp.c:INTERP-001 — raise immortal command trust to ROM tiers`

## Next Intended Task

The remaining `interp.c` work is correctness/cleanup, not security.
Reasonable continuations:

1. **Pure-dispatcher gaps** (smaller, isolated, quick wins):
   - INTERP-002 — snoop forwarding to `desc->snoop_by`
   - INTERP-003 — wiznet `WIZ_SECURE` log mirror for logged commands
   - INTERP-007 — silent return on empty input (Python emits "What?")
   - INTERP-008 — `.`/`,`/`/` punctuation aliases in COMMAND_INDEX
   - INTERP-017 — prefix-match table-order divergence (needs an
     empirical sweep test)
2. **Command-mapping cleanup** (INTERP-009..014): route `hit`, `take`,
   `junk`, `tap`, `go`, `wield`, `hold`, `:` to ROM's canonical
   handlers (`do_kill`, `do_get`, `do_sacrifice`, `do_enter`,
   `do_wear`, `do_immtalk`) rather than separate Python stubs.
3. **INTERP-024** — verify `do_commands`/`do_wizhelp` column format
   and `LEVEL_HERO` mortal/immortal split.

## Outstanding Cleanup (carried over)

- **RNG-isolation flake between integration and unit suites** —
  unchanged from prior sessions.
  `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  passes alone but fails after integration tests run because there's
  no session-scoped `rng_mm.seed_mm` autouse fixture in
  `tests/conftest.py`. Suggested fix:
  `fix(test): isolate rng_mm state across test suites`.
