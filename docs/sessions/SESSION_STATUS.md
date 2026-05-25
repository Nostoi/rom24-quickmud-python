# Session Status — 2026-05-24 — INV-011 CARRY-WEIGHT-COHERENCE locked in

## Current State

- **Active pass**: cross-file invariants — backstop for per-file audits.
- **Last completed**: INV-011 CARRY-WEIGHT-COHERENCE added to
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` with a 5-test
  enforcement suite. Underlying violation closed: `_extract_obj`'s
  carrier branch (`mud/game_loop.py:_remove_from_character`) now
  re-syncs `carry_weight` and `carry_number` after removing the obj
  from inventory/equipment. Version bumped 2.8.78 → 2.8.79.
- **Same-day prior pass**: INV-010 ROOM-PEOPLE-COHERENCE +
  dual-`room_registry` fix (shipped in 2.8.78,
  [SESSION_SUMMARY_2026-05-24_INV010_ROOM_PEOPLE_COHERENCE.md](SESSION_SUMMARY_2026-05-24_INV010_ROOM_PEOPLE_COHERENCE.md)).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-24_INV011_CARRY_WEIGHT_COHERENCE.md](SESSION_SUMMARY_2026-05-24_INV011_CARRY_WEIGHT_COHERENCE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.79 |
| Tests | 4678 passed, 1 pre-existing failure (`test_wait_and_daze_decrement_on_violence_pulse`, present on master) |
| Cross-file invariants | 11 of ~20 budget; INV-001 … INV-011 all ✅ ENFORCED |
| Active focus | Watch list — dual `Object` / `ObjectData` divergence is the highest-value open item |

## Next Intended Task

Consolidate the dual `Object` (`mud/models/object.py`) vs `ObjectData`
(`mud/models/obj.py`) runtime classes. Production builds `Object`;
`object_registry: list[ObjectData]` is never populated, so every
iteration over the "ROM object_list" equivalent
(`mud/mobprog.py`, `mud/world/obj_find.py:get_obj_world`,
`mud/skills/handlers.py` global object scans,
`mud/music/__init__.py`, `mud/game_loop.py:object_update`) is a no-op
in production. This is a multi-session refactor parallel in shape to
INV-008; pick a canonical class, port callers, delete the loser, then
lock in with a new INV-012 OBJECT-LIST-CANONICAL.

Out-of-scope but lingering: the pre-existing
`test_wait_and_daze_decrement_on_violence_pulse` failure on master.

## Push gate

Local commit ready for INV-011 (`feat(parity)`) covering the test,
`_remove_from_character` fix, tracker row, CHANGELOG, version bump,
and this session handoff. Awaiting explicit user approval before
pushing.
