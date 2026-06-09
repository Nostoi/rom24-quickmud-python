# Session Summary — 2026-06-09 — Diff-harness C-oracle scenario for TRIG_EXIT + TRIG_GRALL

## Scope

Continuing from the v2.13.52 docs pass. The next concrete Class 11 deliverable that didn't
require RNG seed alignment was a diff-harness scenario giving `mp_exit_trigger` /
`mp_greet_trigger` C-oracle ground truth rather than Python-authored expectations.
The scenario exercises the two most structurally distinct movement-triggered mobprog
paths: TRIG_EXIT (direction-sensitive, fires and **blocks** movement) and TRIG_GRALL
(percent-based, fires unconditionally on PC arrival).

## Outcomes

### `mob_movement_triggers` scenario — ✅ ADDED (diff-harness C-oracle)

- **Scenario**: `tools/diff_harness/scenarios/mob_movement_triggers.json`
- **Golden**: `tests/data/golden/diff/mob_movement_triggers.golden.json` (12 steps, C binary)
- **ROM C refs**:
  - `src/mob_prog.c:1244-1276` — `mp_exit_trigger`: direction match + position/visibility
    gate for TRIG_EXIT; unconditional direction match for TRIG_EXALL; returns TRUE to
    block movement.
  - `src/mob_prog.c:1309-1345` — `mp_greet_trigger`: TRIG_GRALL path fires when mob not
    at default_pos or cannot see PC; TRIG_GREET gated on default_pos + can_see.
  - `src/act_move.c:move_char` — `if (mp_exit_trigger(ch, door)) return;` early return
    that implements the movement block.
- **Design**: mob 3000 (wizard, default_pos=stand) loaded into room 3001; RNG normalized
  with `__seed=4321` + `__mob_gold=0` / `__mob_silver=0` to prevent spawn-wealth
  divergence. TRIG_EXIT on direction 0 (north): fires on `north`, wizard says "Farewell
  northward traveler!", PC stays in 3001 (movement blocked). TRIG_GRALL at 100%: fires
  when PC returns from 3005 (south), wizard says "Welcome back adventurer!".
- **Tests**: `test_python_matches_c_golden[mob_movement_triggers]` — PASSED. Full suite
  5,479 passed, 5 skipped.

## Files Modified

- `tools/diff_harness/scenarios/mob_movement_triggers.json` — new scenario
- `tests/data/golden/diff/mob_movement_triggers.golden.json` — C-oracle golden (12 steps)
- `CHANGELOG.md` — added [2.13.53] entry
- `pyproject.toml` — 2.13.52 → 2.13.53

## Test Status

- `pytest tests/test_differential_smoke.py -k mob_movement_triggers` — 1/1 PASSED
- All 26 diff-harness tests (smoke + unit): 26 passed, 1 skipped
- Full suite: 5,479 passed, 5 skipped (pre-commit hook clean)

## Next Steps

Class 11 work remaining:

1. **TRIG_GREET ground truth** — the current scenario covers GRALL (no position/visibility
   gate). A companion probe confirming GREET is gated on `mob->position == default_pos`
   and `can_see(mob, ch)` would complete the greet-path coverage. Could be a second
   scenario or an additional step in the existing one.
2. **TRIG_EXALL ground truth** — EXALL fires on any direction with no position/visibility
   gate; a scenario step moving in a non-0 direction would confirm it differs from EXIT.
3. **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — deferred until seed alignment has
   a grounded probe.
4. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the
   next unverified surface outside Class 11.
