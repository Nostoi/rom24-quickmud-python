# Session Status — 2026-04-27 — `interp.c` audit started; social cluster CRITICAL gaps closed

## Current State

- **Active audit**: `interp.c` (Phase 4 — gap closure in progress; 4 of 24 gaps FIXED).
- **Last completed**: INTERP-018, INTERP-019, INTERP-020, INTERP-023 — entire CRITICAL+IMPORTANT social cluster of `check_social`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-27_INTERP_C_SOCIAL_GATES.md](SESSION_SUMMARY_2026-04-27_INTERP_C_SOCIAL_GATES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.6 |
| Tests (socials suite) | 27 / 27 passing |
| ROM C files audited | 16 / 43 (no change — `interp.c` still ⚠️ Partial, but a 24-gap audit doc now exists) |
| `interp.c` gaps closed | 4 / 24 |
| Active focus | `interp.c` — social cluster done; trust table (INTERP-001), dispatcher hooks (INTERP-002/003/008), command-mapping cleanup (INTERP-009..014), and prefix-order sweep (INTERP-017) remain |

## Recent Commits (this session)

- `3577938` — `fix(parity): interp.c:INTERP-018 — socials refuse DEAD/INCAP/MORTAL/STUNNED`
- `7b15bea` — `fix(parity): interp.c:INTERP-019 — sleeping blocks socials except snore`
- `071cdaa` — `fix(parity): interp.c:INTERP-020 — COMM_NOEMOTE silences player socials`
- `9b51e40` — `feat(parity): interp.c:INTERP-023 — NPC slap/echo auto-react to player socials`

## Next Intended Task

Two reasonable continuations:

1. **Finish the social cluster** by closing the remaining 2 gaps:
   `INTERP-021` (`social_registry` should fall back to `str_prefix` lookup
   so `gigg` matches `giggle` per ROM `src/interp.c:584-592`) and
   `INTERP-022` (replace fabricated `social.not_found` field with literal
   `"They aren't here."` per ROM `src/interp.c:637-640`). Both are small
   and isolated to `socials.py` / `social.py`.
2. **Start the trust-table drift cleanup** (`INTERP-001`). The
   `INTERP_C_AUDIT.md` "INTERP-001 detail" table lists ~40 immortal
   commands granted at lower trust than ROM's tier table. This is
   security-relevant (a `LEVEL_IMMORTAL` character can currently
   `reboot`, `purge`, `restore`, `force`, …). Mechanical per-line edits,
   but each command is a separate test + commit per the rom-gap-closer
   rule, so plan for a multi-session sweep.

For dispatcher-side gaps (INTERP-002 snoop, INTERP-003 wiznet log mirror,
INTERP-008 punctuation aliases, INTERP-017 prefix-order sweep), see
`docs/parity/INTERP_C_AUDIT.md` Phase 4 plan.

## Outstanding Cleanup (carried over)

- **RNG-isolation flake between integration and unit suites** — unchanged
  from the prior session.
  `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  passes alone and on master but fails when pytest also collects
  `tests/integration/test_mobprog_*.py`. Root cause: integration
  `conftest.py` autouse seeds `rng_mm.seed_mm(12345)` per integration
  test, but `tests/conftest.py` has no equivalent fixture, so RNG state
  bleeds across suites. Fix: add a session-scoped autouse seed fixture
  to `tests/conftest.py`. Suggested commit prefix
  `fix(test): isolate rng_mm state across test suites`.
