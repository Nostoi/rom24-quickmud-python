# Session Status — 2026-06-01 — INV-025 cancellation PERS masking + shared act_to_room (2.12.29)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.29)**:
  - **INV-025 / PERS masking — `cancellation` wear-off messages now use per-recipient PERS rendering.**
    - `mud/skills/handlers.py:cancellation`'s `_broadcast_room_msg` baked
      `_character_name(target)` into the room broadcast, leaking invisible
      characters' names. Replaced 17 `_broadcast_room_msg("$n ...")` calls
      with `act_to_room(room, "$n ...", target, exclude=target)`, which
      renders `$n` per-recipient through `act_format`→`_pers`→`can_see_character`
      (matching ROM `act(TO_ROOM)`) and dispatches `TRIG_ACT` to NPC recipients.
    - Added `act_to_room()` to `mud/utils/act.py` as the canonical shared
      helper for all `act(TO_ROOM)` surfaces (per-recipient rendering +
      per-NPC `TRIG_ACT` dispatch, matching `src/comm.c:2230-2385`).
    - Refactored `mud/game_loop.py:_act_to_room` and
      `mud/world/movement.py:_act_to_room` to delegate to the shared
      `mud/utils/act.py:act_to_room`, eliminating duplicate code.
    - The module-level `_act_room` in `mud/skills/handlers.py` still uses
      `broadcast_room` + `mp_act_trigger_room` with pre-formatted names (it
      accepts callers that bake `_character_name()` into f-strings). Added a
      NOTE recommending `act_to_room` with `$n`/`$m` tokens for new code.
  - **Tests**: 3 new tests in
    `tests/integration/test_inv025_cancellation_act_pers_masking.py`:
    invisible target blindness wear-off masks name, visible target shows name,
    invisible target sanctuary wear-off masks name.
  - Full integration suite: 2634 passed, 3 skipped.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_INV025_CANCELLATION_PERS_MASKING.md](SESSION_SUMMARY_2026-06-01_INV025_CANCELLATION_PERS_MASKING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.29 |
| Targeted tests | INV-025 cancellation PERS masking: 3 passed; full integration suite: 2634 passed, 3 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | TRAIN-005 remains open in `ACT_MOVE_C_AUDIT.md`; ENTER-018 closed last session |

## Next Intended Task

Continue the cross-file invariant probe pass:
1. Convert remaining `handlers.py:_act_room` callers that bake
   `_character_name()` into f-strings over to `act_to_room` with `$n`/`$m`
   tokens (50+ sites still on the pre-formatted name path — the module-level
   `_act_room` now has a NOTE recommending the shared helper for new code).
2. Review remaining `broadcast_room` call sites in `mud/commands/` for the
   same PERS masking divergence pattern (equipment.py, obj_manipulation.py,
   consumption.py, etc. still bake `char.name`/`ch_name`).
3. If INV-025 / PERS masking surface is exhausted, pick the next standing
   candidate from `CROSS_FILE_INVARIANTS_TRACKER.md`: affect ticks, position
   transitions, or group/follower chain.