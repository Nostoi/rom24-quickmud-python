# Session Summary — 2026-05-30 — GL-025 char_update Ordering

## Scope

Continued cross-file invariants primary pass from
`SESSION_SUMMARY_2026-05-30_INV031_PC_DEATH_PRESERVES_GROUP.md`.

Closed the carried-open `char_update` operation-order divergence. This was
recorded as **GL-025** in `docs/parity/UPDATE_C_AUDIT.md`, not promoted to a
new INV row, because the defect is local ordering inside `char_update` rather
than a new cross-module contract.

## Outcome

### GL-025 — ✅ FIXED (2.11.57)

**ROM verification** (`src/update.c:721-862`):

- PC worn-light decay runs before affect expiry and affect damage.
- Idle timer handling runs before affect expiry and affect damage.
- Drunk/full/thirst/hunger decay runs before affect expiry and affect damage.
- Poison/plague/incap/mortal damage runs after those PC upkeep operations.

**Python divergence**:

`mud/game_loop.py:char_update` ran `tick_spell_effects()` and
`_char_update_tick_effects()` before the PC light/timer/condition block. If a
PC had a worn light with one tick left and a lethal poison/plague tick, Python
processed death first, moved the light into the corpse, then skipped worn-light
decay. ROM burns out the light first, decrements `room.light`, emits burnout
messages, and extracts the light before the lethal affect damage.

**Fix**:

Moved the PC light/timer/condition block before affect expiry and affect damage,
matching ROM order, while preserving affect ticks for connected PCs and
immortals (no early `continue` before `tick_spell_effects()`).

## Files Modified

- `mud/game_loop.py` — reordered `char_update` PC upkeep before affect expiry
  and affect damage.
- `tests/test_game_loop.py` — added
  `test_char_update_decays_light_before_lethal_poison_tick`.
- `docs/parity/UPDATE_C_AUDIT.md` — added GL-025 as fixed.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — updated `update.c` row.
- `CHANGELOG.md` — added GL-025 entry.
- `pyproject.toml` — 2.11.56 → 2.11.57.

## Verification

- `pytest -n0 tests/test_game_loop.py::test_char_update_decays_light_before_lethal_poison_tick -q`
  - fail-first: failed with `room.light == 2`, expected `1`
  - after fix: passed
- `pytest -n0 tests/test_game_loop.py tests/integration/test_update_c_parity.py tests/integration/test_char_update_lethal_tick_iteration.py -q`
  - 33 passed
- `ruff check mud/game_loop.py tests/test_game_loop.py`
  - all checks passed
- `pytest -q`
  - 5092 passed, 4 skipped
- `ruff check .`
  - not clean due pre-existing unrelated repository issues (1,833 reports in
    `.claude/skills`, diagnostic scripts, and unrelated tests); targeted Ruff
    on touched Python files is clean.
- `gitnexus_detect_changes(scope=all)`
  - low risk, 0 affected execution flows

## Outstanding

- Continue cross-file invariant probe/close cycle.
- Mob script trigger contracts beyond INV-025/INV-026.
- Position-transition edge cases during death/recovery.
- INV-025 follow-up sweep: plague tick messages should dispatch TRIG_ACT and
  use PERS masking.
- `Character.pet` type annotation hygiene.
- `curse` handler type annotation hygiene.
