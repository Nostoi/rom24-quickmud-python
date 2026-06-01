# Session Summary — 2026-06-01 — MOVE-004 movement PERS masking

## Scope

Continued the cross-file invariant probe pass after ENTER-017. Re-checked
ROM `src/act_move.c:197,202` directional movement room broadcasts against
Python `mud/world/movement.py`, focusing on the cross-file `act()` contract:
per-recipient PERS name rendering before both delivery and `TRIG_ACT`
dispatch.

## Outcomes

### `MOVE-004` — ✅ FIXED

- **Python**: `mud/world/movement.py:move_character`
- **ROM C**: `src/act_move.c:197,202` + `src/comm.c:2230-2385`
- **Gap**: directional departure/arrival broadcasts baked `char.name` once,
  so an invisible mover's name leaked to unaided room occupants. ROM `act()`
  renders `$n` through `PERS(ch, to)` separately per recipient.
- **Fix**: added `mud/world/movement.py:_act_to_room`, a movement-local
  `act(..., TO_ROOM)` delivery helper that renders `act_format(...)` per
  recipient, delivers through `push_message`, and dispatches `TRIG_ACT` with
  the same recipient-specific buffer.
- **Tests**: added
  `tests/integration/test_inv025_movement_act_trigger_dispatch.py::TestDirectionalDepartureArrival::test_departure_uses_per_recipient_pers_masking`.

## Files Modified

- `mud/world/movement.py` — directional movement room broadcasts now use
  per-recipient `act_format` rendering and recipient-specific `TRIG_ACT`
  dispatch.
- `tests/integration/test_inv025_movement_act_trigger_dispatch.py` — added the
  failing-first PERS masking regression.
- `docs/parity/ACT_MOVE_C_AUDIT.md` — filed and closed MOVE-004.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — updated the INV-025 movement
  follow-up note to include MOVE-004.
- `CHANGELOG.md` — added the MOVE-004 fixed entry.
- `pyproject.toml` — bumped `2.12.26` to `2.12.27`.
- `docs/sessions/SESSION_STATUS.md` — refreshed pointer and next task.

## Test Status

- `pytest -n0 tests/integration/test_inv025_movement_act_trigger_dispatch.py::TestDirectionalDepartureArrival::test_departure_uses_per_recipient_pers_masking -q` — passed after failing red with `HiddenMover leaves north.`.
- `pytest -n0 tests/integration/test_inv025_movement_act_trigger_dispatch.py -q` — 9 passed.
- `pytest -n0 tests/integration/test_inv025_movement_act_trigger_dispatch.py tests/test_movement_followers.py tests/test_movement_visibility.py -q` — 21 passed.
- `pytest -n0 tests/integration/test_inv025_movement_act_trigger_dispatch.py tests/integration/test_act_enter_gaps.py::TestEnter011PortalFadeOut::test_fade_happens_before_greet_trigger tests/integration/test_mobprog_give_trigger.py -q` — 12 passed.
- `ruff check mud/world/movement.py tests/integration/test_inv025_movement_act_trigger_dispatch.py` — clean.

## Next Steps

Continue the cross-file invariant probe pass:

1. Review whether portal movement room broadcasts need the same
   per-recipient PERS treatment as MOVE-004, then file a stable ENTER gap if
   a failing test confirms divergence.
2. If the movement/mobprog surface is exhausted, pick the next standing
   candidate: affect ticks, position transitions, or group/follower chain.
3. Optional hygiene: clean pre-existing Ruff issues in
   `tests/integration/test_act_enter_gaps.py` if targeted lint over that whole
   file is needed.
