# Session Summary — 2026-06-08 — INV-025 object update act triggers

## Scope

Continued from `SESSION_SUMMARY_2026-06-08_INV025_TRIG_ACT_BROADCAST_GAPS.md`.
The remaining INV-025 follow-up was the object-update branch in `mud/game_loop.py`:
object decay messages and object-affect `msg_obj` wear-off messages were still
using pre-rendered `_message_room` / `_send_to_char` paths without the ROM
`act()` side effect that dispatches TRIG_ACT to NPC recipients.

## Outcomes

### Object decay `act(message, rch, obj, TO_ROOM/TO_CHAR)` — ✅ FIXED

- **Python**: `mud/game_loop.py:1248` → `_broadcast_decay`
- **ROM C**: `src/update.c:1014-1022`
- **Fix**: Added object-act trigger helpers that dispatch `mp_act_trigger` with
  `room->people` (`rch`) as the ROM actor and the decaying object as `arg1`.
  `_broadcast_decay` now capitalizes the rendered act line, dispatches TRIG_ACT
  for carrier TO_CHAR delivery, and dispatches room TRIG_ACT for floating-carried
  and in-room object decay messages.
- **Tests**: `tests/test_game_loop.py::test_obj_update_decay_dispatches_trig_act`
  — RED → GREEN.

### Object affect `msg_obj` wear-off — ✅ FIXED

- **Python**: `mud/game_loop.py:1331` → `_broadcast_object_wear_off`
- **ROM C**: `src/update.c:937-951`
- **Fix**: Object `msg_obj` wear-off now capitalizes the rendered act line and
  dispatches TRIG_ACT for in-room `TO_ALL` recipients with `room->people` as
  `rch`. The carried-object branch was also corrected to ROM's TO_CHAR-only
  behavior; Python no longer emits a non-ROM room line or room TRIG_ACT when an
  affect wears off an object in a character's inventory.
- **Tests**:
  - `tests/test_game_loop.py::test_object_affect_wear_off_dispatches_trig_act`
  - `tests/test_game_loop.py::test_carried_object_affect_wear_off_is_to_char_only`

### Tracker / version hygiene — ✅ UPDATED

- **INV-025**: `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` now records the
  object decay / object `msg_obj` wear-off closure and points at the new
  `tests/test_game_loop.py` regressions.
- **INV-029**: same tracker records the object-update TO_CHAR capitalization
  follow-up.
- **Version**: `pyproject.toml` `2.13.35` → `2.13.36`.
- **Changelog**: Added `[2.13.36]` entry.

## Files Modified

- `mud/game_loop.py` — object act-trigger dispatch helpers; decay/wear-off
  trigger dispatch; carried object wear-off TO_CHAR-only correction.
- `tests/test_game_loop.py` — 3 new object-update TRIG_ACT / TO_CHAR-only
  regressions.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — updated INV-025 and INV-029
  touched trails.
- `CHANGELOG.md` — added `[2.13.36]` Fixed entry.
- `pyproject.toml` — `2.13.35` → `2.13.36`.

## Test Status

- `pytest -n0 tests/test_game_loop.py::test_obj_update_decay_dispatches_trig_act tests/test_game_loop.py::test_object_affect_wear_off_dispatches_trig_act tests/test_game_loop.py::test_carried_object_affect_wear_off_is_to_char_only -q` — 3 passed.
- `pytest tests/test_game_loop.py tests/test_obj_update_rom_parity.py tests/integration/test_update_c_parity.py tests/integration/test_inv025_spell_effect_act_trigger.py tests/test_skills_buffs.py -q` — 99 passed.
- `ruff check .` — clean.
- `pytest` — 5458 passed, 5 skipped.
- `gitnexus_detect_changes(scope=all)` — low risk, no affected execution flows.

## Next Steps

The object-update INV-025 follow-up is closed. Next cross-file candidates from
`SESSION_STATUS.md`: widen the deterministic diff-harness state machine with
`give` / `lock` / `unlock` / `pick` command rules, probe `nuke_pets` lifecycle
cleanup against ROM `src/handler.c:nuke_pets`, or verify `TRIG_ENTRY` coverage
when mobs enter rooms through non-player entry paths.
