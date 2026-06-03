# Session Summary — 2026-06-03 — INV-035 mobile mobprog default-position gate

## Scope

Picked up from `SESSION_STATUS.md` after the MOVE-005/MOVE-006 movement work.
The active mode remains cross-file invariants via probe-then-scope. The next
candidate chosen was mobile `TRIG_RANDOM`/`TRIG_DELAY` ordering in ROM
`src/update.c:443-465`.

## Probe Result

ROM `mobile_update` checks mob programs only while the mob is still in its
prototype default position:

- `TRIG_DELAY` runs before `TRIG_RANDOM`.
- If either trigger fires, ROM `continue`s before standing-only AI.
- After the mobprog block, `position != POS_STANDING` stops the mob before
  scavenging/wandering.

Python `mud/ai/__init__.py:mobile_update` already matched this shape:

- resolves `default_pos` and `current_pos`;
- calls `mobprog.mp_delay_trigger` then `mp_random_trigger` only when they match;
- `continue`s on a firing trigger;
- skips `_maybe_scavenge` / `_maybe_wander` when `current_pos != Position.STANDING`.

No production divergence surfaced.

## Outcome — INV-035 (✅ ENFORCED, 2.12.83)

Filed `INV-035 MOBILE-MPROG-DEFAULT-POSITION-GATE` in
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

Added `tests/test_game_loop.py::test_mobile_update_mobprog_default_position_gate_precedes_standing_ai`
to pin both halves of the contract:

- a resting mob whose default is standing does **not** run delay/random triggers;
- a sleeping mob whose default is sleeping **does** run delay then random;
- neither non-standing mob scavenges even when RNG would allow it.

This is a guard for an already-correct contract, not a gap closure.

## Files Modified

- `tests/test_game_loop.py` — new INV-035 regression guard.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — new INV-035 row.
- `CHANGELOG.md` — Added entry for INV-035.
- `pyproject.toml` — version `2.12.82` → `2.12.83`.
- `docs/sessions/SESSION_STATUS.md` — refreshed canonical pointer.

## Verification

- `pytest -n0 tests/test_game_loop.py::test_mobile_update_mobprog_default_position_gate_precedes_standing_ai -q` — passed.
- `pytest -n0 tests/test_game_loop.py -q` — 20 passed.
- `ruff check tests/test_game_loop.py` — clean.
- `ruff check .` — fails on pre-existing lint outside this session's scope
  (`.claude/skills/...`, `diagnostic_test.py`, unrelated test modules); no
  edited Python file errors.
- `gitnexus_detect_changes(scope="all")` — LOW risk, 0 affected processes.

## Next Steps

Candidate next passes:

1. `diff_harness` Hypothesis widening (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — highest-ceiling, multi-day.
2. New cross-INV probe area: position-transition edges or affect ticks.
3. INV tracker consolidation: active enforced count is above the soft ~20-row budget.
