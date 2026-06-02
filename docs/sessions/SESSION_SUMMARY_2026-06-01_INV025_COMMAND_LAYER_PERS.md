# Session Summary — 2026-06-01 — INV-025 command-layer PERS sweep

## Scope

Continuation of the day's INV-025 PERS-masking work (after the magic
`handlers.py` sweep + FIGHT-039/040). Picked up the next SESSION_STATUS task: the
re-probe outside `handlers.py` had found that the command layer (`mud/commands/`)
still emitted ROM `act("$n …", TO_ROOM)` lines as `room.broadcast(f"{char.name}
…")` — no `$n` PERS masking, so an invisible actor leaked its name to unaided
witnesses. This session converted all confirmed command-layer sites.

## Outcomes

### INV-025 command-layer sweep — ✅ CLOSED (commit `ad4ae4aa`, 2.12.48)

- **Python**: `mud/commands/advancement.py`, `session.py`, `notes.py`.
- **ROM C**: `act("$n …", TO_ROOM)` at `act_info.c:2779/2787` (practice),
  `act_move.c:1760/1777/1798` (train durability/power/`$T` stat),
  `act_move.c:1575/1618/1621` (recall pray/disappear/appear),
  `board.c:503/1181` (note start/finish).
- **Gap**: 10 sites baked `char.name` into `room.broadcast` — no per-recipient
  `$n` PERS masking (invisible actor leaked; visible NPC would render the baked
  name rather than `short_descr`). The two note lines also **dropped the
  `{G..{x` colour** and the finish line used a hand-rolled `_possessive` helper
  instead of ROM's `$s`.
- **Fix**: all → `act_to_room(room, "$n …", char, exclude=char)`, each verified
  against its exact ROM `act()` string (`$T`/`$s` tokens, `{G` colour). Removed
  the now-orphaned `notes._possessive` helper (act_format's `$s` replaces it).
- **Tests**: new `tests/integration/test_inv025_command_layer_pers.py` (do_recall
  pray + do_train durability: invisible actor → "Someone", visible → name).
  Re-baselined `test_do_practice_command.py::test_practice_room_messages` — it had
  mocked `room.broadcast` (the old delivery mechanism); rewritten to assert the
  ROM line via a sighted witness's messages. 264 other existing assertions
  (train/recall/practice/boards/advancement) stayed green (visible PCs render the
  same name).

## Files Modified

- `mud/commands/advancement.py` — 5 broadcasts (practice ×2, train ×3) → act_to_room.
- `mud/commands/session.py` — 3 broadcasts (recall pray/disappear/appear) → act_to_room.
- `mud/commands/notes.py` — 2 broadcasts (note start/finish, `{G` colour + `$s`) → act_to_room; removed `_possessive`.
- `tests/integration/test_inv025_command_layer_pers.py` — new masking test.
- `tests/integration/test_do_practice_command.py` — re-baselined to witness-based assertion.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 trail: command-layer sweep CLOSED.
- `CHANGELOG.md`, `pyproject.toml` (2.12.47 → 2.12.48), `README.md` (test count).

## Test Status

- New + re-baselined files green; 264 related existing assertions green.
- Full suite caught a missed re-baseline (`test_do_practice_command` mocked the
  retired `room.broadcast`) — fixed to a sighted-witness assertion; re-run green:
  **5259 passed, 4 skipped** (`pytest -p no:xdist -o addopts="" -q`, ~11.5 min).
- `act_to_room` consumes no RNG → no global RNG-sequence shift.

## Next Steps

1. **Finish the INV-025 baked-name re-probe** — `mud/combat/`, `mud/world/`, and
   `mud/commands/communication.py` (`do_say`/`do_tell`) for the same
   `room.broadcast(f"…{name}…")` pattern that bypasses `act_to_room` PERS masking.
2. Other cross-file-invariants candidate areas (position transitions, mob script
   triggers) remain once the PERS sweep is exhausted.
