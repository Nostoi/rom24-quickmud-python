# Session Summary — 2026-05-24 — `skills.c` game-loop integration

## Scope

Closed the remaining `skills.c` tracker note that still marked integration coverage as partial. The work focused on the real runtime path: skill command execution, combat state entry, and `game_tick()`-driven `PULSE_VIOLENCE` progression, with ROM `src/fight.c` and `src/update.c` used as the source of truth for timer cadence.

## Outcomes

### `skills.c` integration coverage — ✅ CLOSED

- **Python**: `mud/game_loop.py:1274`, `mud/combat/engine.py:323`
- **ROM C**: `src/fight.c:192-196`, `src/fight.c:2952`, `src/update.c:1116-1161`
- **Gap**: `skills.c` tracker note — integration tests were still marked `⚠️ Partial (need game loop integration)`
- **Fix**: Restored ROM timer cadence semantics in the runtime path. Connected characters still burn `wait`/`daze` one pulse at a time; descriptor-less actors now burn those timers on `PULSE_VIOLENCE` boundaries instead of every Python tick. Removed the stale hardcoded timer decrement from `multi_hit()`.
- **Tests**: Added/updated runtime-path assertions in `tests/integration/test_skills_integration.py`; targeted skill/combat slice green; full integration suite green.

## Files Modified

- `mud/game_loop.py` — split wait/daze recovery by descriptor presence and violence cadence.
- `mud/combat/engine.py` — removed redundant descriptor-less timer decrement from `multi_hit()`.
- `tests/integration/test_skills_integration.py` — added `game_tick()` combat-cadence coverage and ROM-faithful wait-state recovery assertions.
- `tests/test_combat_rom_parity.py` — updated stale timer expectation to the restored runtime model.
- `tests/test_skills.py` — marks the wait-recovery unit as a connected-character path.
- `tests/test_skills_learned.py` — aligns learned-skill wait recovery with connected-character semantics.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — flipped `skills.c` integration note to complete.
- `docs/parity/INTEGRATION_TEST_COVERAGE_TRACKER.md` — refreshed the skills integration counts and notes.
- `CHANGELOG.md` — added `2.8.71` changelog entries.
- `pyproject.toml` — bumped `2.8.70 → 2.8.71`.

## Test Status

- `pytest tests/integration/test_skills_integration.py tests/integration/test_skills_integration_combat_specials.py tests/test_skills.py tests/test_skills_learned.py tests/test_combat_rom_parity.py -v` — `63 passed, 1 skipped`
- `pytest tests/integration/ -v` — `2108 passed, 3 skipped`
- `ruff check .` — fails on pre-existing unrelated lint debt outside this slice (notably `.claude/skills/*`, `diagnostic_test.py`, and legacy test modules)

## Next Steps

The next tracker continuation is `magic.c + magic2.c`, which still shows `Integration Tests: ⚠️ Partial (need affect persistence tests)`. The concrete next slice is to add the missing spell/game-loop integration coverage around affect persistence and duration handling through `game_tick()`.
