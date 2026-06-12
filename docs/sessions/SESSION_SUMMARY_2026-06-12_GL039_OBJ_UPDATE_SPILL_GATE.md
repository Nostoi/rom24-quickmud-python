# Session Summary — 2026-06-12 — GL-039: obj_update spill gate uses wear_flags instead of wear_loc

## Scope

Continuation from v2.14.8 (FIGHT-061 closed). The session ran six cross-file invariant probe
candidates listed in the previous handoff — `do_recall` movement cost, `violence_update` mid-tick
death, `do_rescue` stop-fighting order, hit/mana/move regen math, and `gain_condition` tick — plus
one additional probe of `obj_update` spill gate logic in `mud/game_loop.py`.

Five probes were clean; one real divergence was found in `obj_update` (GL-039).

## Probe Results

| Candidate | ROM C reference | Python equivalent | Verdict |
|-----------|----------------|-------------------|---------|
| `do_recall` movement cost | `src/act_move.c:do_recall` | `mud/commands/session.py:do_recall` | ✅ CLEAN — `ch.move //= 2` matches ROM `ch->move /= 2`; move is non-negative so `//` = C `/` |
| `violence_update` mid-tick death | `src/fight.c:63-103` | `mud/game_loop.py:violence_tick` | ✅ CLEAN — Python snapshots `list(reversed(character_registry))` before loop; post-`multi_hit` guard `if getattr(ch, "fighting", None) is not victim: continue` handles mid-tick death correctly |
| `do_rescue` stop-fighting / multi-hit order | `src/fight.c:3094-3099` | `mud/skills/handlers.py:rescue` | ✅ CLEAN — order is `stop_fighting(foe)` → `stop_fighting(target)` → `check_killer` → `set_fighting(caster, foe)` → `set_fighting(foe, caster)`, matching ROM exactly |
| `hit_gain` / `mana_gain` / `move_gain` regen math | `src/update.c:130-230` | `mud/game_loop.py` | ✅ CLEAN — operands are provably non-negative; `//` is correct. No `c_div`/`c_mod` needed |
| `gain_condition` tick | `src/update.c:258-326` | `mud/characters/conditions.py:gain_condition` | ✅ CLEAN — delta==0 guard, NPC/immortal guards, -1 (permanent) guard, `max(0, min(48, ...))` = ROM `URANGE`, hunger/thirst/drunk messages only at 0 |
| `obj_update` spill gate | `src/update.c:1025-1026` | `mud/game_loop.py:obj_update` | ❌ DIVERGENCE — extra `elif` branch used prototype `wear_flags & ITEM_WEAR_FLOAT` instead of runtime `wear_loc == WEAR_FLOAT` → filed+closed as GL-039 |

## Outcomes

### `GL-039` — ✅ FIXED

- **Python**: `mud/game_loop.py:obj_update` (spill gate block)
- **ROM C**: `src/update.c:1025-1026`
- **Gap**: ROM's `obj_update` spill-gate (`if obj->contains`) enters the spill branch only when
  `obj->item_type == ITEM_CORPSE_PC` OR `obj->wear_loc == WEAR_FLOAT`. Python had an additional
  `elif` that also spilled when `obj->item_type == ITEM_CONTAINER` AND `wear_flags & ITEM_WEAR_FLOAT`.
  This means a floating-capable container that is **not currently floating** (wear_loc = -1) would
  incorrectly spill its contents into the room instead of having them destroyed recursively by
  `_extract_obj`. A disc with the FLOAT capability flag stored in inventory or on the ground would
  leak its contents on decay instead of destroying them silently.
- **Fix**: Removed the extra `elif` branch. Spill gate now checks runtime state only:
  `item_type == CORPSE_PC` OR `wear_loc == FLOAT`.
- **Tests**: `tests/integration/test_gl039_obj_update_spill_gate.py` (2 cases):
  - `test_non_floating_container_contents_destroyed_not_spilled` — disc with `wear_flags=WEAR_FLOAT`
    but `wear_loc=-1`; after `obj_update`: disc AND gem both gone from `object_registry`, gem NOT in
    room (not spilled).
  - `test_currently_floating_container_contents_spilled` — disc with `wear_loc=FLOAT` (actively
    floating); after `obj_update`: gem survives in room (spilled correctly).
  Both verified red before fix, green after.
- **Regression fix**: `tests/test_game_loop.py::test_obj_update_spills_floating_container` was also
  updated to set `wear_loc=int(WearLocation.FLOAT)` on the chest fixture — the old test was silently
  relying on the wrong `wear_flags` branch to pass, so it would have regressed after the fix without
  the correction.

## Files Modified

- `mud/game_loop.py` — removed extra `elif wear_flags & ITEM_WEAR_FLOAT` spill branch from
  `obj_update`; added ROM C citation comment (`# mirroring ROM src/update.c:1025-1026`)
- `tests/integration/test_gl039_obj_update_spill_gate.py` — new integration test (2 cases)
- `tests/test_game_loop.py` — added `wear_loc=int(WearLocation.FLOAT)` to chest fixture in
  `test_obj_update_spills_floating_container`; added docstring with ROM C reference
- `docs/parity/UPDATE_C_AUDIT.md` — added GL-039 row (✅ FIXED 2.14.9)
- `CHANGELOG.md` — added `[2.14.9]` Fixed entry
- `pyproject.toml` — 2.14.8 → 2.14.9

## Test Status

- `pytest tests/integration/test_gl039_obj_update_spill_gate.py -n0` — 2/2 passing
- `pytest tests/test_game_loop.py -n0` — 28/28 passing (no regression)
- Full suite: **5616/5616 passing** (collected, post-fix)

## Next Steps

All six probe candidates from this session have been verified. GL-039 is closed. The cross-file
invariants pass continues. Suggested next probe areas:

1. **`obj_update` timer-decay ordering** — ROM `src/update.c:970-1005` decrements `timer` and
   then acts on `timer <= 0`. Verify Python `obj_update` timer decrement happens before the decay
   branch and not after.
2. **`affect_update` count-down ordering** — ROM `src/update.c:330-420` processes affects by
   decrement-first; verify Python `mud/game_loop.py:affect_update` (or `mud/affects/engine.py`)
   follows the same order vs post-processing.
3. **`do_look` / `do_exits` room-darkness flag** — ROM `src/act_info.c:look_in_room` guards
   on `room->light` and `IS_SET(room->room_flags, ROOM_DARK)`. Verify Python's darkness check
   uses the same two conditions in the same precedence.
