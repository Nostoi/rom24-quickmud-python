# Session Summary — 2026-06-01 — ENTER-018 portal PERS masking

## Scope

Continued the cross-file invariant probe pass after MOVE-004. The
directional-movement PERS masking fix exposed the same divergence in the
portal movement path: `move_character_through_portal` and `_portal_fade_out`
used `broadcast_room()` (single baked string, no per-recipient rendering)
instead of `_act_to_room()` (per-recipient PERS masking via `act_format` + per-NPC
TRIG_ACT dispatch). ROM `src/act_enter.c:134,151-154,204,209-210` all use
`act(TO_ROOM)`, which renders `$n` through `PERS(ch, recipient) / can_see()`
separately for each watcher before delivery.

## Outcomes

### `ENTER-018` — ✅ FIXED

- **Python**: `mud/world/movement.py:move_character_through_portal` (lines 582-584,
  608-613) + `_portal_fade_out` (lines 671-673, 679-684)
- **ROM C**: `src/act_enter.c:134,151-154,204,209-210`
- **Gap**: portal departure, arrival, and fade-out broadcasts baked
  `char.name` once via `broadcast_room()`, so an invisible traveller's
  name leaked to unaided room occupants. ROM `act()` renders `$n` through
  `PERS(ch, to)` separately per recipient.
- **Fix**: replaced 4 `broadcast_room()` + `mp_act_trigger_room()` pairs with
  `_act_to_room()` calls, matching the directional-movement path fixed in
  MOVE-004. Removed now-unused `broadcast_room` import from `movement.py`.
- **Tests**: added
  `tests/integration/test_inv025_movement_act_trigger_dispatch.py::TestPortalPERSMasking`
  (2 tests: `test_portal_departure_masks_invisible_actor`,
  `test_portal_arrival_masks_invisible_actor`).

## Files Modified

- `mud/world/movement.py` — portal departure/arrival/fade-out broadcasts now
  use per-recipient `act_format` rendering and per-NPC `TRIG_ACT` dispatch;
  removed `broadcast_room` import.
- `tests/integration/test_inv025_movement_act_trigger_dispatch.py` — added
  `TestPortalPERSMasking` class (2 failing-first tests).
- `docs/parity/ACT_ENTER_C_AUDIT.md` — filed and closed ENTER-018; updated
  summary counts (17 gaps, all closed).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — updated INV-025 row
  with ENTER-018 portal PERS masking note.
- `CHANGELOG.md` — added ENTER-018 / INV-025 fixed entry.
- `pyproject.toml` — bumped `2.12.27` to `2.12.28`.

## Test Status

- `pytest -n0 tests/integration/test_inv025_movement_act_trigger_dispatch.py -q` — 11 passed.
- `pytest tests/integration/ -x -n0 --timeout=60` — 2631 passed, 3 skipped.
- `ruff check mud/world/movement.py` — clean.

## Next Steps

Continue the cross-file invariant probe pass:

1. Review remaining `broadcast_room` call sites in `mud/` for the same PERS
   masking divergence (INV-027 surface). The directional and portal paths are
   now covered; check combat/death/position-change, spec_funs, and communication
   paths that still use `broadcast_room`.
2. If the INV-025 / movement surface is exhausted, pick the next standing
   candidate from `CROSS_FILE_INVARIANTS_TRACKER.md`: affect ticks, position
   transitions, or group/follower chain.
3. Optional hygiene: clean pre-existing Ruff issues in test files if targeted.