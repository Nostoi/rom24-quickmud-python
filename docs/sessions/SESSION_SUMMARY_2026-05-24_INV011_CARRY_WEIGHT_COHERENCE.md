# Session Summary — 2026-05-24 — INV-011 CARRY-WEIGHT-COHERENCE

(Second pass on the cross-file invariants list this day; follows
[SESSION_SUMMARY_2026-05-24_INV010_ROOM_PEOPLE_COHERENCE.md](SESSION_SUMMARY_2026-05-24_INV010_ROOM_PEOPLE_COHERENCE.md).)

## Outcome

- New cross-file invariant **INV-011 CARRY-WEIGHT-COHERENCE** added to
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`, locked in by a
  5-test enforcement suite in
  `tests/integration/test_inv011_carry_weight_coherence.py`.
- Underlying violation discovered and closed:
  `mud/game_loop.py:_remove_from_character` removed obj from
  `character.inventory` / `character.equipment` without resyncing
  `carry_weight` or decrementing `carry_number`. Every `_extract_obj`
  on a carried object (corpse decay, item decay, magic destroy) drifted
  encumbrance upward. ROM routes through `obj_from_char`
  (`src/handler.c:1642`) which keeps both counters in lockstep.
- Bonus discovery (deferred to watch list): the runtime is built on
  **two distinct Object classes** — `mud.models.object.Object` (used
  by `spawn_object` and production) vs
  `mud.models.obj.ObjectData` (the class `object_registry` is typed
  against). Nothing ever appends to `object_registry`, so every
  iteration over the "ROM object_list" equivalent is a no-op in
  production: mobprog oload triggers, `get_obj_world`, locate-object,
  object decay. Parallel shape to INV-008. Too large for one session
  — captured in the tracker's watch list pending a consolidation
  strategy.
- Version bumped 2.8.78 → **2.8.79**. CHANGELOG updated.

## Files touched

- `mud/game_loop.py:_remove_from_character` — after inventory/
  equipment removal, decrement `carry_number` by the obj's slot cost
  and call `character._recalculate_carry_weight()`. Mirrors ROM
  `obj_from_char`.
- `tests/integration/test_inv011_carry_weight_coherence.py` — new
  file, 5 enforcement tests.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-011 row
  added (in numerical order with INV-010). Watch list updated:
  added the dual `Object`/`ObjectData` divergence as the most
  load-bearing open candidate; struck through the now-closed
  INV-010 and INV-011 candidates while keeping the audit trail.
- `CHANGELOG.md` — `[2.8.79]` section.
- `pyproject.toml` — version bump 2.8.78 → 2.8.79.

## Tests

`pytest tests/integration/test_inv011_carry_weight_coherence.py -v`
→ 5 passed (2 of those red against master before the
`_remove_from_character` fix landed).

Full suite: 4678 passed, 1 pre-existing failure
(`tests/test_game_loop_wait_daze.py::test_wait_and_daze_decrement_on_violence_pulse`,
unchanged from the INV-010 session — still on master, still out of
scope for the cross-file pass).

## INV-011 contract (for posterity)

> For every `Character ch`:
> - `ch.carry_weight == sum(_object_carry_weight(o) for o in ch.inventory) + sum(_object_carry_weight(o) for o in ch.equipment.values())`
> - `ch.carry_number == sum(_object_carry_number(o) for o in ch.inventory) + sum(_object_carry_number(o) for o in ch.equipment.values())`
>
> Canonical mutators: `Character.add_object` / `equip_object` /
> `remove_object`. Runtime extract paths must also re-sync via
> `_recalculate_carry_weight` + carry_number decrement —
> `mud/game_loop.py:_remove_from_character` now does so.

## Followups for next session

1. **Dual `Object` / `ObjectData` consolidation** (watch list, high
   priority). The cross-file shape is parallel to INV-008: pick one
   class as canonical, port the other's callers, delete the loser. This
   unblocks oload triggers, locate-object spells, mobprog room scans,
   and object decay — all currently no-ops because `object_registry`
   is never populated. Multi-session refactor, but the payoff is
   visible game behavior.
2. `test_wait_and_daze_decrement_on_violence_pulse` triage (still
   pre-existing on master).

## Push gate

Local commit ready. Awaiting explicit user approval before pushing.
