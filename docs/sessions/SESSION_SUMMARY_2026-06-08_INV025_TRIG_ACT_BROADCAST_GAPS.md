# Session Summary — 2026-06-08 — INV-025 TRIG_ACT broadcast gaps

## Scope

Continued from the previous session (v2.13.33 — Hypothesis broke-keeper sell
rules). All three next candidates from `SESSION_STATUS.md` had been addressed
last session (position-transitions clean, affect_strip clean, Hypothesis
broke-keeper done). This session probed for new cross-file invariant candidates
by systematically walking every `broadcast_room` and `_message_room` callsite
in `mud/` and comparing them against their ROM C `act(TO_ROOM)` counterparts to
check for missing `mp_act_trigger` dispatch (INV-025 class).

## Outcomes

### Scavenger pickup `"$n gets $p."` — ✅ FIXED

- **Python**: `mud/ai/__init__.py:194` → `_take_object`
- **ROM C**: `src/update.c:491` — `act("$n gets $p.", ch, obj_best, NULL, TO_ROOM)`
- **Fix**: Replaced `room.broadcast(f"{mob_name} gets {obj_name}.")` with
  `act_to_room(room, "$n gets $p.", mob, arg1=obj, exclude=mob)`. Also removed the
  dead `_broadcast_room` helper in `mud/ai/__init__.py` (never called; used the
  wrong delivery path — `messages` list instead of `push_message`).
- **Tests**: `test_scavenger_pickup_dispatches_trig_act` in
  `tests/test_game_loop.py` — 1 new test, RED → GREEN.

### Four `_message_room` callsites in `game_loop.py` — ✅ FIXED

All four sites correspond to ROM `act(TO_ROOM)` calls with no `MOBtrigger = FALSE`
guard; Python was using `_message_room` (baked f-string broadcast, no trigger)
instead of `_act_to_room` (per-recipient formatting + TRIG_ACT dispatch).

- **Python**: `mud/game_loop.py`
- **ROM C sources**:
  - `src/update.c:693` — `act("$n wanders on home.", TO_ROOM)` — NPC out-of-zone
  - `src/update.c:857` — `act("$n shivers and suffers.", TO_ROOM)` — poison tick
  - `src/update.c:745` — `act("$n disappears into the void.", TO_ROOM)` — linkdead
  - `src/update.c:727` — `act("$p goes out.", TO_ROOM)` — worn light extinguish
- **Fix**: All four replaced with `_act_to_room(room, "<template>", character, ...)`
  which delegates to `act_to_room` from `mud/utils/act.py` (per-recipient `$n`/`$p`
  formatting + `mp_act_trigger` per NPC recipient).
- **Tests**: 2 new tests in `tests/test_game_loop.py`:
  - `test_wanders_home_dispatches_trig_act`
  - `test_poison_shiver_dispatches_trig_act`

### INV-025 broadcast surface probe — ✅ CLEAN (existing coverage)

All other `broadcast_room` and `act_to_room` callsites verified clean:

- `mud/commands/doors.py:213,304` — linked-room open/close messages → already
  followed by `mp_reverse_act_trigger_room` ✅
- `mud/skills/handlers.py:118` — `_act_room` calls both `broadcast_room` AND
  `mp_act_trigger_room` ✅
- `mud/spec_funs.py` — `_broadcast_room` (line 843) calls `mp_act_trigger_room` ✅
- `mud/world/movement.py` — `_act_to_room` → `act_to_room` (trigger-wired) ✅
- `mud/commands/position.py` — position transitions use `act_to_room` ✅

### Remaining `_message_room` callsites (object decay/wear-off) — noted, not yet fixed

Lines 1214, 1228, 1295, 1299 in `game_loop.py` handle object decay and object
affect wear-off messages. These use pre-baked/rendered strings from
`_render_obj_message` where the ROM C "actor" is `rch` (first person in room),
not a protagonist character. Fixing these requires either converting to an
`mp_act_trigger_room` post-dispatch or restructuring the object-message rendering
pipeline. Noted as the next follow-up in this area; not filed as a new INV row
(same INV-025 ad-hoc category).

## Files Modified

- `mud/ai/__init__.py` — replaced baked broadcast with `act_to_room`; removed
  dead `_broadcast_room` helper
- `mud/game_loop.py` — four `_message_room` → `_act_to_room` conversions
- `tests/test_game_loop.py` — 3 new TRIG_ACT dispatch tests
- `CHANGELOG.md` — added [2.13.34] and [2.13.35] Fixed entries
- `pyproject.toml` — 2.13.33 → 2.13.35

## Test Status

- `pytest tests/test_game_loop.py` — 23 passed
- `pytest tests/integration/test_inv025_spell_effect_act_trigger.py` — 12 passed
- Full suite: **5451 passed, 5 skipped** (5456 collected; +3 new tests vs 2.13.33)

## Next Steps

1. **Object decay / object affect wear-off TRIG_ACT** (`mud/game_loop.py:1214,
   1228, 1295, 1299`): remaining `_message_room` callsites for `obj_update` decay
   messages and `_broadcast_object_wear_off` — these map to ROM `src/update.c:1017-
   1022` `act(message, rch, obj, TO_ROOM)`. Fix requires either routing through
   `act_to_room` with `rch` as the actor, or a direct `mp_act_trigger_room` call
   alongside the existing `_message_room`.
2. **Hypothesis state machine widening** (Class 11 dynamic widening, ongoing):
   continue Phase C — additional command/watch-set rules (e.g. `give`, `lock`,
   `unlock`, `pick`, `pray`). The most natural extension is commands that produce
   multi-step state transitions the harness can exercise deterministically.
3. **Cross-file invariant candidates not yet probed**: `nuke_pets` lifecycle
   (`src/handler.c` vs `mud/characters/`), `TRIG_ENTRY` call site coverage
   (mob enters room), `do_order` / `do_gtell` group-command act() dispatch.
