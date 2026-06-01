# Session Summary — 2026-06-01 — INV-025 cancellation PERS masking + shared act_to_room

## Scope

Continued the cross-file invariant probe pass after ENTER-018. The `handlers.py`
`cancellation` function's wear-off messages used `_broadcast_room_msg`, which
baked `_character_name(target)` once and broadcast it via `broadcast_room` —
leaking invisible characters' names to unaided room occupants. ROM
`src/magic.c:1062-1196` uses `act("$n is no longer blinded.", victim, NULL, NULL, TO_ROOM)`
for every wear-off line, so `comm.c:2230-2385` renders `$n` through
`PERS(victim, recipient) / can_see()` separately for each watcher.

## Outcomes

### INV-025 — cancellation wear-off PERS masking ✅ FIXED

- **Python**: `mud/skills/handlers.py:cancellation` replaced 17
  `_broadcast_room_msg("$n ...")` calls with
  `act_to_room(room, "$n ...", target, exclude=target)`.
- **Shared helper**: Added `mud/utils/act.py:act_to_room()` as the canonical
  `act(TO_ROOM)` delivery function — iterates room occupants, renders per
  recipient via `act_format` (which applies INV-027 PERS masking through
  `_pers`→`can_see_character`), delivers via `push_message`, and dispatches
  `TRIG_ACT` per NPC (gated by `MOBtrigger`).
- **Refactor**: `mud/game_loop.py:_act_to_room` and
  `mud/world/movement.py:_act_to_room` now delegate to the shared
  `mud/utils/act.py:act_to_room`, eliminating duplicate per-recipient
  rendering loops.
- **Note**: The module-level `_act_room` in `mud/skills/handlers.py` (line 103)
  still uses `broadcast_room` + `mp_act_trigger_room` with pre-formatted
  names. It accepts callers that bake `_character_name()` into f-strings,
  which bypass PERS masking. A NOTE was added recommending `act_to_room`
  with `$n`/`$m` tokens for new code. Converting all 50+ callers is a
  follow-up task, not this session's scope.

### Tests

- `tests/integration/test_inv025_cancellation_act_pers_masking.py` — 3 tests:
  - `test_invisible_mob_blindness_wear_off_masks_name`: invisible target →
    onlooker sees "Someone is no longer blinded."
  - `test_visible_mob_blindness_wear_off_shows_name`: visible target →
    onlooker sees "Verdana is no longer blinded."
  - `test_invisible_mob_sanctuary_wear_off_masks_name`: invisible target →
    onlooker sees "The white aura around someone's body vanishes."
- Full integration suite: 2634 passed, 3 skipped.
- Ruff: no new issues.

## Files Modified

- `mud/utils/act.py` — added `act_to_room()` (shared `act(TO_ROOM)` delivery
  with per-recipient PERS masking and per-NPC TRIG_ACT dispatch).
- `mud/skills/handlers.py` — replaced `_broadcast_room_msg` inside
  `cancellation` with `act_to_room` calls; added `act_to_room` import;
  added NOTE to `_act_room` recommending shared helper.
- `mud/game_loop.py` — `_act_to_room` delegates to shared `act_to_room`;
  removed unused `act_format` import.
- `mud/world/movement.py` — `_act_to_room` delegates to shared `act_to_room`;
  removed unused `push_message` import.
- `tests/integration/test_inv025_cancellation_act_pers_masking.py` — new
  (3 tests: PERS masking for cancellation wear-off messages).
- `CHANGELOG.md` — added INV-025 cancellation PERS masking entry.
- `pyproject.toml` — bumped `2.12.28` to `2.12.29`.

## Next Steps

1. Convert remaining `handlers.py:_act_room` callers that bake
   `_character_name()` into f-strings to use `act_to_room` with `$n`/`$m`
   tokens — this is the broadest remaining PERS masking surface (50+ sites).
2. Review remaining `broadcast_room` call sites in `mud/commands/` for the
   same pattern (equipment.py, obj_manipulation.py, consumption.py, etc.).
3. Continue the cross-file invariant probe pass per
   `CROSS_FILE_INVARIANTS_TRACKER.md`.