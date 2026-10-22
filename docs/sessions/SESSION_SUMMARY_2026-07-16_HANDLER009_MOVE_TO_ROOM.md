# Session Summary — 2026-07-16 — HANDLER-009 closed (move_to_room head-insert)

## Scope

Autonomous loop iteration 9/10. Closed **HANDLER-009**: `MobInstance.
move_to_room` appended to `room.people`, inverting ROM `char_to_room`'s
newest-arrival-first order (`src/handler.c:1557-1559`).

## Outcomes

### `HANDLER-009` — ✅ FIXED

- **Python**: `mud/spawning/templates.py:MobInstance.move_to_room` — now
  routes through `Room.add_mob` (head-insert; the same chokepoint production
  paths already used).
- **ROM C**: `src/handler.c:1557-1559` — `char_to_room` prepends
  (`ch->next_in_room = pRoomIndex->people; pRoomIndex->people = ch;`).
- **Reach**: test-only today, but latent for any future caller — a
  tail-append corrupts every room-people walk (look listings, check_assist's
  outer loop, the INV-045 room-head seed).
- **Tests**: `tests/integration/test_handler009_move_to_room_head_insert.py`
  (2, failing-first: newest-arrival head; departure + arrival ordering).
- **Fixture fallout (1)**: `test_shop_room_broadcasts.py`'s act-trigger
  witness was a SECOND grocer (vnum 3002) placed via move_to_room — under
  ROM head-insert it becomes the room head and wins `find_keeper`'s scan
  (exactly what ROM would do), so `buy lantern` resolved to the
  lantern-less witness. Witness replaced with a shop-less mob (3064, the
  drunk).
- **Commit**: `bdd45e6c` (v2.14.331).

## Session note

The session process restarted mid-verification (harness restart, not a test
failure); the resumed run re-verified cleanly.

## Files Modified

- `mud/spawning/templates.py` — move_to_room → Room.add_mob
- `tests/integration/test_handler009_move_to_room_head_insert.py` — new (2)
- `tests/integration/test_shop_room_broadcasts.py` — witness fixture
- `docs/parity/HANDLER_C_AUDIT.md` — HANDLER-009 ✅
- `CHANGELOG.md`, `pyproject.toml` — 2.14.330 → 2.14.331

## Test Status

- Unit **2801 passed, 1 skipped**; integration **3443 passed, 3 skipped**.
- Differential harness: 102/102 across 69 scenarios.

## Next Steps

Final loop iteration (10/10). Remaining carry-overs: DESC-001, OLC
spell-name lookup, IS_BUILDER, stray `data/quickmud.db` / `doc/game.db`
cleanup. Recommended: close what fits, then write the loop-final handoff
(the 10-iteration retrospective) so the operator has a single review
surface for the ~18 unpushed commits.
