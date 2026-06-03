# Session Summary — 2026-06-03 — FINDING-020 equip→remove carry-list position (2.13.6)

## Scope

Picked up from the room-contents `show_list_to_char` session (2.13.5). The
per-file audit tracker is exhausted; active mode is the cross-file /
divergence-class sweep. FINDING-020 was the one significant open item in the
class-13 (object-list head-insert) divergence — explicitly parked "for its own
scoped session" three times. User selected it as this session's focus.

The work was decision-first: ROM's exact equip→remove ordering had to be
captured from the C engine *before* choosing an implementation, because the
naive "store an absolute carry-list index" approach is unfaithful.

## Outcomes

### FINDING-020 — equip→remove must preserve ROM's carry-list position — ✅ RESOLVED (PC path)

- **Python**: `mud/commands/obj_manipulation.py:_remove_obj`,
  `mud/models/character.py:add_object` / `equip_object`,
  `mud/models/object.py:Object._carry_seq`
- **ROM C**: `src/handler.c` `equip_char` / `unequip_char` (set/clear `wear_loc`
  only) + `obj_to_char` (LIFO head-insert); `get_eq_char` loops `ch->carrying`
- **Gap**: ROM never removes an equipped object from `ch->carrying` — only
  `wear_loc` flips — so a removed item keeps its original carry-list slot. The
  Python port stored equipped objects in a separate `equipment` dict and
  re-**appended** them to `inventory` on remove, landing them at the tail.
- **C ground truth (diffshim oracle)** — position is **relative to acquisition
  order**, not a fixed index:
  - sword acquired *after* bag → returns in front: `[3021, 3032]`
  - sword acquired *first*, then bag+jacket → returns at tail: `[3045, 3032, 3021]`
  - sword re-acquired from a container → returns to head: `[3021, 3045, 3032]`
  This ruled out an absolute-index fix.
- **Fix**: acquisition-sequence shim — a global monotonic `Object._carry_seq`
  stamped at every carry-list entry (`Character.add_object`; `equip_object`
  direct-equip else-branch). On unequip, `_remove_obj` re-inserts the object
  ahead of the first carried object with a lower `_carry_seq` (descending-
  acquisition order) instead of appending. Behaviorally isomorphic to ROM's
  single carry list, while keeping the enforced `char.equipment` dict convention.
- **Tests**: `tests/integration/test_finding020_equip_remove_carry_position.py`
  — 3 C-confirmed scenarios, 3/3 passing. Also un-gated the diff-harness
  generated state machine's `remove` rules (removed the `_no_other_carried()`
  restriction) so Hypothesis exercises the formerly-divergent remove-with-other-
  carried path against the live C oracle. Direct C-vs-Python diff confirmed match
  for inventory **and** equipment across findings/interleave/roundtrip + two-equip/
  re-equip/drop-mix.

## Out-of-scope findings filed (durable, per AGENTS.md)

- **FINDING-024 (OPEN)** — save/load discards inventory↔equipment carry-list
  ordering. `equipment_state` is a dict with no position relative to the ordered
  `inventory_state`; reloaded equipped items have no `_carry_seq`, so a reloaded-
  then-removed item appends. Persistence leg of the same divergence.
- **FINDING-025 (OPEN)** — `MobInstance.equip` (`templates.py:512`, `# stub`)
  uses a different equipment representation than PCs: keeps the item in
  `inventory` with `wear_loc` set and never populates the equipment dict. Mob
  disarm/remove position is not verified by this fix. Both filed in
  `tools/diff_harness/FINDINGS.md`.

## Files Modified

- `mud/models/object.py` — added `Object._carry_seq` field (acquisition order)
- `mud/models/character.py` — `_carry_seq_counter`/`_next_carry_seq`; stamp in
  `add_object` and `equip_object` direct-equip branch
- `mud/commands/obj_manipulation.py` — `_remove_obj` re-inserts by descending seq
- `tools/diff_harness/generated.py` — un-gated `remove` rules; dropped
  `_no_other_carried` helper
- `tests/integration/test_finding020_equip_remove_carry_position.py` — new, 3 tests
- `tools/diff_harness/FINDINGS.md` — FINDING-020 → RESOLVED (PC-scoped);
  new FINDING-024, FINDING-025
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class-13 row + to-do #6/#7 updated
- `CHANGELOG.md` — Fixed entry; `pyproject.toml` — 2.13.5 → 2.13.6

## Test Status

- New: `test_finding020_equip_remove_carry_position.py` — 3/3 passing
- Diff-harness: `test_diff_harness_generated.py` + `test_differential_smoke.py`
  + `test_diff_harness_unit.py` — 22/22 (live C oracle, un-gated remove path)
- Equipment/inventory/object regression slice — 381 passed, 1 skipped
- Full suite: **5417 passed, 4 skipped** (`pytest`, 0 failures)
- `ruff check` / `ruff format --check` on touched files — clean
- `gitnexus_detect_changes` — risk LOW, 0 affected processes

## Next Steps

1. **FINDING-024** — save/load persistence leg: persist `_carry_seq` per object
   (or restore the carry list inline by re-equipping in order). Needs a diff-
   harness save/reload scenario (diffshim has no save step today) or a focused
   persistence test.
2. **FINDING-025** — probe the mob equip representation: does mob disarm preserve
   carry-list position, and is the missing equipment-dict entry a real divergence
   or a benign alternate model? ROM uses one carry-list+`wear_loc` model for both.
3. Continue Phase C deterministic diff-harness widening (light hold, money/shop
   paths); add RNG-locked combat only after seed alignment is proven.
