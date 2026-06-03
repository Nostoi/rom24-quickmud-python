# Session Summary — 2026-06-03 — Room-contents look() + FINDING-022 commit (2.13.5)

## Scope

Picked up from the class-13 bypass sweep session (2.13.3–2.13.4, uncommitted).
Committed the FINDING-022 + class-13 bypass dump (2.13.4), then ported the
room-contents `look()` display through `show_list_to_char` — the last
unfilled consumer of the newly-shared formatting function.

## Outcomes

### FINDING-022 + class-13 bypass sweep — ✅ COMMITTED (2.13.4)

- Committed the uncommitted working-tree changes from the prior session:
  FINDING-022 (look-in container indent), FINDING-023 (fire_effect dead-code
  room.objects), and 15 INV-039 bypass-site fixes.
- 24 files changed, 823 insertions, 133 deletions.
- Full suite: 5404 passed, 4 skipped.

### Room-contents `look()` parity — ✅ FIXED (2.13.5)

- **Python**: `mud/world/look.py:_look_room` (lines 171-179)
- **ROM C**: `src/act_info.c:1106 show_list_to_char(ch->in_room->contents, ch, FALSE, FALSE)`
- **Gap**: `_look_room` used a hand-rolled `for obj in room.contents` loop that
  emitted bare `obj.description` lines, missing:
  1. `can_see_object` visibility filter — invisible objects shown without DETECT_INVIS
  2. Aura prefixes — (Invis), (Red Aura), (Blue Aura), (Magical), (Glowing), (Humming)
  3. COMBINE duplicate coalescence — NPC/COMBINE viewers should see (N) counts or
     5-space padding for singletons
  4. Non-COMBINE PC formatting — one line per visible object, no indent
- **Fix**: replaced the hand-rolled loop with `show_list_to_char(room.contents, char,
  f_short=False, f_show_nothing=False)`, matching ROM's `src/act_info.c:1106` call.
  The shared `show_list_to_char` already handles all four gaps.
- **Tests**: `tests/integration/test_room_contents_show_list_parity.py` — 10 tests:
  - ground objects shown by description (not short_descr)
  - invisible object hidden without DETECT_INVIS
  - invisible object visible with (Invis) prefix when DETECT_INVIS
  - empty room shows no "Nothing." line
  - glowing object gets (Glowing) prefix
  - object with no description is hidden
  - COMBINE viewer sees (N) count for duplicates
  - COMBINE viewer sees 5-space padding for singles
  - Non-COMBINE PC sees no indent/padding
  - Dark room hides objects entirely

## Files Modified

- `mud/world/look.py` — `_look_room`: replaced hand-rolled room-contents loop with
  `show_list_to_char(room.contents, char, f_short=False, f_show_nothing=False)`
- `tests/integration/test_room_contents_show_list_parity.py` — new, 10 tests
- `CHANGELOG.md` — added room-contents parity entry under [Unreleased]
- `pyproject.toml` — 2.13.4 → 2.13.5
- `docs/sessions/SESSION_STATUS.md` — updated to current state

## Test Status

- New tests: `test_room_contents_show_list_parity.py` — 10/10 passing
- Prior related: `test_finding022_show_list_to_char_parity.py` — 11/11 passing
- Look area slice (`-k "look"`): 86 passed, 1 skipped
- Full suite: **5414 passed, 4 skipped** (`pytest`, 0 failures)
- `ruff check mud/world/look.py mud/utils/act.py` — clean

## Next Steps

1. **FINDING-020** — equipment-dict carry-list position divergence. ROM keeps
   equipped objects in `ch->carrying` with `wear_loc` set; removing an item
   merely clears `wear_loc`, preserving position. Python stores equipped objects
   in `char.equipment` dict (removed from `inventory` on equip) and re-appends
   on remove, so removed items always land at the tail. A faithful fix requires
   either (a) re-architecting to ROM's carry-list-with-wear_loc model, or (b)
   tracking original position and re-inserting at that position on remove — both
   are significant changes needing their own scoped session.
2. Continue Phase C diff-harness widening (light hold, money/shop paths);
   add RNG-locked combat only after seed alignment is proven.
3. Optional: unify `do_inventory`'s COMBINE logic with `show_list_to_char`
   (not required for parity — both produce correct output independently).