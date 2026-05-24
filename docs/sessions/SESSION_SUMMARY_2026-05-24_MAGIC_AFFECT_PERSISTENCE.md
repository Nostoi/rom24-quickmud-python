# Session Summary — 2026-05-24 — magic affect persistence

## Scope

Picked up the `magic.c + magic2.c` integration follow-up from `SESSION_STATUS.md` and closed the tracker note that still marked spell-affect persistence as partial. The session targeted the real runtime path only: `game_tick()` → `char_update()` → `tick_spell_effects()`, with ROM `src/update.c` as the source of truth for duration decay, per-tick level fade, and wear-off delivery.

## Outcomes

### `tick_spell_effects` — ✅ FIXED

- **Python**: `mud/affects/engine.py:9`
- **ROM C**: `src/update.c:765-784`
- **Gap**: `magic.c + magic2.c` tracker note — integration tests were still partial, and the runtime path was missing ROM's 20% spell-strength fade during affect ticking.
- **Fix**: Added the missing `rng_mm.number_range(0, 4) == 0` level-fade logic to the character affect ticker so spell `level` now decays through the same `char_update()` path ROM uses.
- **Tests**: `tests/integration/test_spell_affects_persistence.py` expanded with 3 new runtime-path cases; targeted file green (`24 passed`).

### `magic.c + magic2.c` integration note — ✅ CLOSED

- **Python**: `tests/integration/test_spell_affects_persistence.py:1`
- **ROM C**: `src/update.c:765-784`
- **Gap**: Tracker note `Integration Tests: ⚠️ Partial (need affect persistence tests)`
- **Fix**: Added coverage for three ROM contracts: no decay before `PULSE_TICK`, affect `level` can fade on the point pulse, and multi-entry affects wear off once through `game_tick()`.
- **Tests**: Full integration suite green after the additions (`2111 passed, 3 skipped`).

## Files Modified

- `mud/affects/engine.py` — restored ROM point-pulse affect-level fade in `tick_spell_effects()`.
- `tests/integration/test_spell_affects_persistence.py` — added runtime-path persistence, level-decay, and single wear-off coverage.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — closed the `magic.c + magic2.c` integration-note row.
- `CHANGELOG.md` — added `2.8.72` entries for the runtime parity fix and new integration coverage.
- `pyproject.toml` — bumped version `2.8.71` → `2.8.72`.

## Test Status

- `pytest tests/integration/test_spell_affects_persistence.py -q` — `24 passed`
- `pytest tests/test_affects.py tests/integration/test_spell_affects_persistence.py -q` — `47 passed`
- `pytest tests/integration/ -v` — `2111 passed, 3 skipped`
- `ruff check .` — fails on pre-existing unrelated lint debt in `.claude/skills/`, `diagnostic_test.py`, and assorted historical test files; no new lint issue introduced in touched files

## Next Steps

The `magic.c + magic2.c` integration note is now closed. The remaining documented gap in that row is still `spell_pass_door()`; the next session can either finish that last 2% on the magic row or move to the next tracker-selected partial/not-audited subsystem if priorities shift.
