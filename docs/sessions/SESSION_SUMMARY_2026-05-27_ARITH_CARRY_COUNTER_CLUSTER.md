# Session Summary — 2026-05-27 — ARITH carry-counter cluster (ARITH-106/108/109/112/113) closed in 2.9.74

## Scope

Continuation of the META Class 2 ARITHMETIC_BOUNDARY close-out. Picked
up the carry-weight/carry-number cluster identified in
`SESSION_STATUS.md` as the next intended task: five sites that wrapped
ROM's `ch->carry_weight -= ...` / `ch->carry_number -= ...` subtractions
(`src/handler.c:1678-1679`) in `max(0, ...)` floors that silently
absorbed double-extract / over-subtract corruption. Closed in one
commit (the precedent from ARITH-101/102/103 `create_money` cluster).

## Outcomes

### `ARITH-106` — ✅ FIXED

- **Python**: `mud/models/character.py:580`
- **ROM C**: `src/handler.c:1678 obj_from_char`
- **Gap**: ARITH-106 — `Character.remove_object` floored `carry_number` at 0
- **Fix**: `self.carry_number -= carry_delta` (bare subtraction). `_recalculate_carry_weight()` continues to handle the weight side via fresh sum.
- **Tests**: `tests/integration/test_obj_from_char_no_floor.py::test_character_remove_object_allows_negative_carry_number` — passing.

### `ARITH-108` / `ARITH-109` — ✅ FIXED

- **Python**: `mud/commands/obj_manipulation.py:638-640` (`_obj_from_char`)
- **ROM C**: `src/handler.c:1678-1679`
- **Gap**: ARITH-108 (carry_weight floor) + ARITH-109 (carry_number floor)
- **Fix**: Both `max(0, ...)` wrappers removed; raw `getattr(char, ..., 0) - delta` subtraction now matches ROM.
- **Tests**: `tests/integration/test_obj_from_char_no_floor.py::test_obj_from_char_allows_negative_carry_weight_and_number` — passing.

### `ARITH-112` / `ARITH-113` — ✅ FIXED

- **Python**: `mud/commands/consumption.py:347-351` (`_destroy_object`)
- **ROM C**: `src/handler.c:1678-1679`
- **Gap**: ARITH-112 (carry_weight floor) + ARITH-113 (carry_number floor) — sibling consumption-path duplicates of ARITH-108/109
- **Fix**: Both `max(0, ...)` wrappers removed; raw subtraction now matches ROM.
- **Tests**: `tests/integration/test_obj_from_char_no_floor.py::test_destroy_object_allows_negative_carry_weight_and_number` — passing.

## Files Modified

- `mud/models/character.py` — `Character.remove_object` floor removed (ARITH-106)
- `mud/commands/obj_manipulation.py` — `_obj_from_char` floors removed (ARITH-108/109)
- `mud/commands/consumption.py` — `_destroy_object` floors removed (ARITH-112/113)
- `tests/integration/test_obj_from_char_no_floor.py` — new (3 regression cases)
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — rows 15/21/22/29/30 flipped to ✅ FIXED; header tally updated (14 FIXED / 13 N/A / 19 ❌ MISSING open)
- `CHANGELOG.md` — added 2.9.74 Fixed entry covering all five gap IDs
- `pyproject.toml` — 2.9.73 → 2.9.74

## Test Status

- `pytest tests/integration/test_obj_from_char_no_floor.py -v` — **3/3 passing**
- Full integration suite: **2337 passed, 3 skipped** in 85.66s
- `ruff check` on touched files — clean (preexisting `I001` / `F401` in other functions in the same files left untouched, consistent with prior session policy)

## Outstanding (filed during this session)

None — all five gaps closed cleanly; no new bugs surfaced. Pre-existing
pyright warnings in unrelated areas of the touched files
(`mud/commands/consumption.py:128,285`, `mud/commands/obj_manipulation.py`
star-prefix unused-arg warnings) confirmed unchanged by this session's
edits.

## Next Steps

1. **Push approval** — branch is now **7 commits** ahead of `origin/master`
   (2.9.70 / 2.9.71 / 2.9.72 / 2.9.73 / two prior handoffs / **2.9.74**).
   Verify with `git log origin/master..HEAD`.
2. **Level-0 spell/skill dice cluster** — ARITH-020/021/022/023. Reachable
   via mob-program or scripted dispatch per the audit doc; probe ROM source
   first to see whether each is real divergence or dead defensive code.
3. **ARITH-107** — `area.nplayer` floor at `mud/models/room.py:171` in
   `char_from_room`. Same shape as the carry-counter cluster
   (`max(0, current - 1)` where ROM does raw `--ch->in_room->area->nplayer`).
   Probably another one-commit closure if no upstream guard exists.
4. **ARITH-111** — held-back item-shop haggle floor. Needs the
   `deduct_cost`-with-negative-cost analysis described in audit row 26.
5. **ARITH-114** — PC-ceiling divergence on `get_curr_stat` (Python flat
   25 vs ROM per-race/class `max_stat`). Lower priority — only matters
   above stat-22.
6. **Pre-existing lint** still parked (handler.py:566-567 F841, etc.).
7. **GitNexus FTS** — read-only-DB warnings continued throughout this
   session; documented upstream issue, node/edge graph unaffected.
