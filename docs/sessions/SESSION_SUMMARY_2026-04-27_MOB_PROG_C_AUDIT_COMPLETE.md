# Session Summary — 2026-04-27 — `mob_prog.c` audit complete (all 7 gaps closed)

## Outcome

`mob_prog.c` ROM parity audit complete. All 7 gaps closed:

| Gap | Severity | Subject |
|-----|----------|---------|
| MOBPROG-001 | CRITICAL | `objexists` walks the world (mirrors `get_obj_world`) |
| MOBPROG-002 | CRITICAL | `mp_greet_trigger` GREET/GRALL exclusivity (no fall-through after failed percent roll) |
| MOBPROG-003 | IMPORTANT | `vnum $n` against PC compares against `lval=0` instead of returning False |
| MOBPROG-004 | IMPORTANT | `clan` / `race` / `class` checks resolve name keyword via ROM-style prefix lookup |
| MOBPROG-005 | IMPORTANT | `else` resets `state[level] = IN_BLOCK` (structural parity only — see audit doc) |
| MOBPROG-006 | IMPORTANT | `$R` $-code replicates ROM `ch`-vs-`rch` bug |
| MOBPROG-007 | MINOR    | Invalid `if`/`or`/`and` keyword logs warning and aborts program |

Tracker row in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` flipped from
⚠️ Partial 75% → ✅ Complete 100%.

## Files Touched

- `mud/mobprog.py` — fixes for all 7 gaps + `_KNOWN_IF_CHECKS` set + `_rom_prefix_lookup` helper + module logger
- `tests/integration/test_mobprog_predicates.py` — new file (8 tests covering MOBPROG-001/003/004/006)
- `tests/integration/test_mobprog_greet_trigger.py` — new file (2 tests covering MOBPROG-002)
- `tests/integration/test_mobprog_program_flow.py` — new file (2 tests covering MOBPROG-005 regression + MOBPROG-007 abort)
- `tests/integration/test_mobprog_scenarios.py` — fixture program corrected to use real ROM keyword `carries` (was previously-silent invalid `has_item`)
- `docs/parity/MOB_PROG_C_AUDIT.md` — Phase 4 closure notes; all rows ✅ FIXED
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `mob_prog.c` row updated
- `CHANGELOG.md` — `[2.6.5]` block with 7 `Fixed` bullets
- `pyproject.toml` — version bumped 2.6.4 → 2.6.5

## Recent Commits

- `4616ec5` — `fix(parity): mob_prog.c:MOBPROG-001 — objexists walks the world`
- `f0b96db` — `fix(parity): mob_prog.c:MOBPROG-002 — greet/grall exclusivity`
- `e256989` — `fix(parity): mob_prog.c:MOBPROG-003 — vnum check vs PC uses lval=0`
- `7459114` — `fix(parity): mob_prog.c:MOBPROG-004 — clan/race/class name lookup`
- `1b4ca24` — `fix(parity): mob_prog.c:MOBPROG-005 — else resets state[level] to IN_BLOCK`
- `4e11263` — `fix(parity): mob_prog.c:MOBPROG-006 — $R replicates ROM ch-vs-rch bug`
- `645b40c` — `fix(parity): mob_prog.c:MOBPROG-007 — invalid if-check aborts with bug log`

## Test Status

`pytest tests/integration/test_mobprog_*.py tests/test_mobprog*.py` ⇒ all green
except the documented pre-existing failures:

- `tests/test_mobprog_triggers.py::test_event_hooks_fire_rom_triggers`
- `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  (RNG-state pollution flake when integration suite runs before this unit
  test — passes alone on master; not introduced by this session.)

Full suite was not re-run after the work for environmental reasons (the
full `pytest` invocation hangs in this shell session even on master before
this session's changes).

## Notes for Next Session

- Pick the next P1 file from `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
  for audit. Remaining P1 candidates with non-100% status are listed there.
- The pre-existing flaky `test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  is a known RNG-isolation gap between integration and unit suites; tracking
  it as a separate task is overdue.
