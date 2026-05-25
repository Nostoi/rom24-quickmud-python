# Session Summary — 2026-05-24 — INV-010 ROOM-PEOPLE-COHERENCE

## Outcome

- New cross-file invariant **INV-010 ROOM-PEOPLE-COHERENCE** added to
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`, locked in by a
  6-test enforcement suite in
  `tests/integration/test_inv010_room_people_coherence.py`.
- Underlying violation discovered and closed: `mud/models/room.py`
  declared a second `room_registry` dict that the world loader never
  populated, so `char_to_room`'s NULL → temple fallback and
  `mud/game_loop.py:525`'s limbo lookup both silently no-opped against
  an empty dict. Fix: re-export the canonical `mud.registry.room_registry`
  from `mud/models/room.py`.
- Version bumped to **2.8.78**. CHANGELOG updated. Cross-file tracker
  gains a "Watch list" section with two candidate INVs for future
  sessions (object_list / extract_obj cleanup, carry_weight coherence).

## Files touched

- `mud/models/room.py` — removed the duplicate module-local
  `room_registry` declaration, re-imported the canonical one from
  `mud.registry`. No behavior change for any caller already importing
  from `mud.registry`; `mud/game_loop.py:33` and the in-module temple
  fallback now resolve against the populated table.
- `tests/integration/test_inv010_room_people_coherence.py` — new file,
  6 enforcement tests.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-010 row added,
  watch list section added for INV-011 / INV-012 candidates.
- `CHANGELOG.md` — `[2.8.78]` section.
- `pyproject.toml` — version bump 2.8.77 → 2.8.78.

## Tests

`pytest tests/integration/test_inv010_room_people_coherence.py -v` →
6 passed.

Full suite: 4673 passed, 1 pre-existing failure
(`tests/test_game_loop_wait_daze.py::test_wait_and_daze_decrement_on_violence_pulse`)
— **confirmed present on master before this work** by stashing and
re-running; not introduced here.

## INV-010 contract (for posterity)

> For every `Character ch`, `ch.room` is `R` iff `ch in R.people`. The
> only mutation paths are `Room.add_character` / `Room.remove_character`
> (and the `char_to_room` wrapper). All other call sites
> (`do_recall`, `MobInstance.move_to_room`, `imm_load`, `imm_search`,
> `imm_commands._char_from_room/_char_to_room`, `spec_funs` mayor patrol)
> are partial duplicates that must keep both sides of the contract in
> sync.

## Followups for next session

1. The cross-file tracker's **watch list** names two candidates:
   - object-side analogue of INV-003 (object_list membership +
     `extract_obj` cleanup across room/char/container/global list)
   - `carry_weight` / `carry_number` coherence with `char.inventory`
     across get/drop/give/equip/unequip paths.
   Either is a plausible INV-011 if a regression surfaces or as a
   proactive lock-in.
2. The pre-existing `test_wait_and_daze_decrement_on_violence_pulse`
   failure on master needs triage but is **out of scope** for the
   cross-file invariants pass — it's a unit-test-vs-game_loop pulse
   counter issue, not a cross-module contract.
3. `SESSION_STATUS.md` had drifted (claimed 2.8.73 while
   `pyproject.toml` was 2.8.77). Refreshed to 2.8.78 in this session.

## Push gate

Local commits only. No `origin/master` push without explicit user
approval per the cross-file invariants playbook.
