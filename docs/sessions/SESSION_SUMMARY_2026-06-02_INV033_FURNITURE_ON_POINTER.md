# Session Summary — 2026-06-02 — INV-033 FURNITURE-ON-POINTER-COHERENCE

## Scope

Cross-file invariants is the sole active pass (no per-file audit gaps remain).
Picked up from the prior session's recommended probe — **position transitions**
(`do_stand`/`do_sit`/`do_rest`/`do_sleep`/`do_wake`, `src/act_move.c`). The
voluntary position commands themselves are a faithful port; the cross-file
contract they depend on is the `ch->on` **furniture pointer**, which links a
Character to a furniture Object and is read by `count_users` (capacity) and the
per-tick regen heal/mana bonus. Probed the coherence of that pointer across the
two ROM primitives that clear it (`char_from_room`, `obj_from_room`) and found a
real gap on the object-removal side.

## Outcomes

### `INV-033` — ✅ CLOSED / ENFORCED (FURNITURE-ON-POINTER-COHERENCE)

- **Python**: `mud/game_loop.py:_extract_obj` (the INV-014 canonical recursive
  extractor) — added the occupant `on`-pointer sweep to its `in_room` branch.
- **ROM C**: `src/handler.c:1904-1917 obj_from_room` (clears every
  `in_room->people` occupant whose `ch->on == obj`); routed through
  `src/handler.c:2052-2058 extract_obj`. The char-leave counterpart
  `src/handler.c:1530-1532 char_from_room` was already mirrored in
  `Room.remove_character` (`mud/models/room.py:163-165`).
- **Gap**: `_extract_obj` removed furniture from `room.contents` but never
  cleared occupants' `on`. Furniture that **decayed or was purged out from
  under a sitter** (`obj_update` decay tick, `do_purge`, mob purge) left a
  dangling `ch.on` that kept feeding the furniture regen bonus
  (`hit_gain`/`mana_gain` read `ch->on->value[3]`/`value[4]`, ROM
  `src/update.c:217-218,299-300`) from furniture that no longer existed, and
  corrupted the no-arg `do_rest`/`do_sit`/`do_sleep` default (`obj = ch->on`).
- **Fix**: in `_extract_obj`'s `room is not None` branch, iterate `room.people`
  and clear `occupant.on` for every char with `on is obj` before removing the
  object from `room.contents` — a strict no-op for non-furniture, so the 6
  callers' behaviour for normal objects (potions, corpses, lights) is unchanged.
- **Guarded cousins (verified, not open)**: `do_get`
  (`mud/commands/inventory.py:254-264`, ROM `src/act_obj.c:126-134` occupancy
  check) and `do_sacrifice` (`mud/commands/obj_manipulation.py:419-425`) both
  refuse to remove furniture someone is `on` — so those vectors never reach the
  stranding state. The unguarded vectors (decay/purge/extract) all funnel
  through `_extract_obj`, the single enforcement point → true ✅ ENFORCED, not a
  partial claim.
- **Impact**: `gitnexus_impact({target: "_extract_obj"})` = **HIGH** (6 direct
  callers: decay tick, `do_purge`, mob purge/`_extract_character`,
  `_destroy_light`, `_spill_contents`, the obj-manipulation wrapper). Reported
  to user; the no-op-for-non-furniture property bounds the risk.
- **Tests**: `tests/integration/test_inv033_furniture_on_pointer_coherence.py`
  (4 tests: direct extract clears all occupants; decay-tick clears; unrelated-
  object extract is a no-op; regen heal bonus stops once `on` cleared) — 4/4
  passing. `gitnexus_detect_changes` = low risk (change contained to
  `_extract_obj`, no affected processes).

## Files Modified

- `mud/game_loop.py` — `_extract_obj` clears occupants' `ch.on` on room-removal
  (mirrors ROM `obj_from_room`).
- `tests/integration/test_inv033_furniture_on_pointer_coherence.py` — new, 4 tests.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added INV-033 row (✅ ENFORCED).
- `CHANGELOG.md` — added INV-033 `Fixed` entry under `[Unreleased]`.
- `pyproject.toml` — 2.12.65 → 2.12.66.

## Test Status

- `pytest tests/integration/test_inv033_furniture_on_pointer_coherence.py` — 4/4.
- Targeted regression (extract/decay/furniture/position): 84/84.
- Full suite: **5333 passed, 4 skipped** (~140s parallel) — zero fallout from the
  HIGH-blast-radius `_extract_obj` change.

## Next Steps

Cross-file invariants remains the active pass. Tracker is now at **26 enforced**
INV rows — past the ~20 soft cap AGENTS.md flags ("if it grows past ~20 entries,
the per-file methodology itself needs revisiting"). INV-033 was filed
deliberately (a clean new named contract); a future session should decide
whether to consolidate (the INV-014/INV-015 precedent merged paired rows) before
adding more. Remaining uncovered cross-file candidates: **group/follower chain**
ordering and **mob trigger** ordering. Probe-then-scope: read ROM C contract →
read Python equivalent → one failing test → close as a gap or file as the next
free INV-NNN (INV-034).

> **Push note:** 2.12.66 (`8d6e982e`) is **pushed to `origin/master`**
> (`0301b452..8d6e982e`). The prior 2.12.65 commits had already been pushed —
> `origin/master` sat at `0301b452` before this push — so this push carried only
> the INV-033 commit. `master` and `origin/master` are now in sync.
