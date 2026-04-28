# Session Status — 2026-04-27 — `interp.c` social cluster complete

## Current State

- **Active audit**: `interp.c` (Phase 4 — gap closure in progress;
  6 of 24 gaps FIXED; full social cluster of `check_social` complete).
- **Last completed**: INTERP-021 (`str_prefix` social lookup),
  INTERP-022 (literal "They aren't here."). Closes the 6-gap social
  cluster (INTERP-018/019/020/021/022/023).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-27_INTERP_C_SOCIAL_CLUSTER_COMPLETE.md](SESSION_SUMMARY_2026-04-27_INTERP_C_SOCIAL_CLUSTER_COMPLETE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.7 |
| Tests (socials suite) | 31 / 31 passing |
| ROM C files audited | 16 / 43 (no change — `interp.c` still ⚠️ Partial) |
| `interp.c` gaps closed | 6 / 24 (25%) |
| Active focus | `interp.c` — social cluster complete; trust table (INTERP-001), dispatcher hooks (INTERP-002/003/007/008), command-mapping cleanup (INTERP-009..014), and prefix-order sweep (INTERP-017) remain |

## Recent Commits (this session)

- `b9e4bf2` — `fix(parity): interp.c:INTERP-021 — social lookup uses str_prefix`
- `b57ef3e` — `fix(parity): interp.c:INTERP-022 — literal "They aren't here." on missing target`

## Next Intended Task

Highest leverage remaining `interp.c` work:

1. **`INTERP-001` — trust-table drift sweep** (~40 immortal commands
   granted at lower trust than ROM's `merc.h:147-167` tier table).
   Security-relevant (a `LEVEL_IMMORTAL` character can currently
   `reboot`, `purge`, `restore`, `force`, …). Mechanical per-row
   edits, but rom-gap-closer requires one commit + one test per row,
   so plan for a multi-session sweep. See "INTERP-001 detail" table
   in `docs/parity/INTERP_C_AUDIT.md`.
2. **Pure-dispatcher gaps**: INTERP-002 (snoop forwarding), INTERP-003
   (wiznet `WIZ_SECURE` log mirror), INTERP-007 (silent empty input),
   INTERP-008 (`.`/`,`/`/` aliases), INTERP-017 (prefix-match
   table-order sweep — needs an empirical test).
3. **Command-mapping cleanup**: INTERP-009..014 — `hit`, `take`,
   `junk`, `tap`, `go`, `wield`, `hold`, `:` should dispatch to ROM's
   canonical handlers (`do_kill`, `do_get`, `do_sacrifice`, `do_enter`,
   `do_wear`, `do_immtalk`) rather than separate Python stubs.

## Outstanding Cleanup (carried over)

- **RNG-isolation flake between integration and unit suites** —
  unchanged from prior sessions.
  `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  passes alone but fails after integration tests run because there's
  no session-scoped `rng_mm.seed_mm` autouse fixture in
  `tests/conftest.py`. Fix: add the fixture. Suggested commit prefix
  `fix(test): isolate rng_mm state across test suites`.
