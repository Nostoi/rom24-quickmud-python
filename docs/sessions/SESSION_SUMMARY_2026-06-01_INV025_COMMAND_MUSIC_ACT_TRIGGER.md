# Session Summary — 2026-06-01 — INV-025 command/music/level-fail/Mota ACT trigger dispatch (2.12.24)

## Scope

Continued the INV-025 cross-file-invariant sweep. The previous session closed spell-effect, healer, and spec_fun surfaces. This session targeted the remaining surfaces identified in SESSION_STATUS:

1. Music jukebox broadcasts (`mud/music/__init__.py:_broadcast_jukebox_message`)
2. Command broadcasts (`do_pose`, `_broadcast_level_fail`, Mota decline, remaining audit)

## Outcomes

### Music jukebox `act(TO_ALL)` — ✅ CLOSED

- **Python**: `mud/music/__init__.py:_broadcast_jukebox_message` — added per-NPC `mp_act_trigger` dispatch after the per-occupant `_push_music_message` delivery loop. The trigger message formats `$p` for each NPC recipient, matching ROM `src/music.c:128,154` `act(buf, room->people, obj, NULL, TO_ALL)`.

### `do_pose` `act(TO_ROOM)` — ✅ CLOSED

- **Python**: `mud/commands/communication.py:do_pose` — added `mp_act_trigger_room` dispatch after `broadcast_room`, matching ROM `src/act_comm.c:1420` `act(pose_table[...].message, ch, NULL, NULL, TO_ROOM)`.

### `_broadcast_level_fail` `act(TO_ROOM)` — ✅ CLOSED

- **Python**: `mud/commands/equipment.py:_broadcast_level_fail` — added `mp_act_trigger_room` dispatch after `broadcast_room`, matching ROM `src/act_obj.c:1410` `act("$n tries to use $p, but is too inexperienced.", ch, obj, NULL, TO_ROOM)`.

### Mota decline `act(TO_ROOM)` — ✅ CLOSED

- **Python**: `mud/commands/obj_manipulation.py:do_sacrifice` — added `mp_act_trigger_room` dispatch after the Mota decline `broadcast_room`, matching ROM `src/act_obj.c:1782` `act("$n offers $mself to Mota, who graciously declines.", ch, NULL, NULL, TO_ROOM)`.

## Files Modified

- `mud/music/__init__.py` — added per-NPC `mp_act_trigger` dispatch to `_broadcast_jukebox_message`.
- `mud/commands/communication.py` — added `mp_act_trigger_room` dispatch in `do_pose`.
- `mud/commands/equipment.py` — added `mp_act_trigger_room` dispatch in `_broadcast_level_fail`.
- `mud/commands/obj_manipulation.py` — added `mp_act_trigger_room` import and dispatch in Mota decline branch.
- `tests/integration/test_inv025_spell_effect_act_trigger.py` — added 4 new test classes (12 total): `TestMusicJukeboxActTrigger`, `TestPoseActTrigger`, `TestBroadcastLevelFailActTrigger`, `TestMotaDeclineActTrigger`.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — updated INV-025 row with new surfaces.
- `docs/sessions/SESSION_STATUS.md` — updated to 2.12.24.
- `CHANGELOG.md` — added INV-025 jukebox/pose/level-fail/Mota entry under Fixed.
- `pyproject.toml` — 2.12.23 → 2.12.24.

## Test Status

- `pytest tests/integration/test_inv025_spell_effect_act_trigger.py -v` — 12/12 passed.
- `pytest -n0 tests/integration/test_inv025_*.py -v` — 78/78 passed.
- `pytest tests/integration/test_music_play.py tests/integration/test_music_load_songs.py` — all passed.
- `pytest -n0 tests/integration/test_music_play.py tests/integration/test_music_load_songs.py tests/test_music.py -v` — 19/19 passed.
- `ruff check` — clean on all modified files. Full `ruff check .` still reports pre-existing issues outside this session's touched files.

## INV-025 Sweep Status

The INV-025 principle (`every act() drives mp_act_trigger for NPC recipients`) is now fully applied to all `broadcast_room` and `act(TO_ROOM)`/`act(TO_ALL)` call sites in production Python code:

- Combat broadcasts ✅ (prior sessions)
- Equipment/get/put/drop/give ✅ (prior sessions)
- Door/open/close/lock/unlock/pick ✅ (prior sessions)
- Movement/quit/scan ✅ (prior sessions)
- Consumption/liquid ✅ (prior sessions)
- Thief/steal ✅ (prior sessions)
- Imm command broadcasts ✅ (prior sessions)
- Communication act() ✅ (prior sessions)
- Spell-effect broadcasts ✅ (prior sessions)
- Healer utterance ✅ (prior sessions)
- Spec_fun broadcasts ✅ (prior sessions)
- **Music jukebox ✅ (this session)**
- **do_pose ✅ (this session)**
- **_broadcast_level_fail ✅ (this session)**
- **Mota decline ✅ (this session)**

`broadcast_global` (channel) paths are ROM `descriptor_list` per-PC delivery that bypasses `mp_act_trigger` — no gaps.
