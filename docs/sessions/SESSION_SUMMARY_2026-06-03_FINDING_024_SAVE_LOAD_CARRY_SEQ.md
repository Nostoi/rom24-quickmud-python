# Session Summary — 2026-06-03 — FINDING-024 save/load carry-list ordering (2.13.7)

## Scope

Picked up from `SESSION_SUMMARY_2026-06-03_FINDING_020_CARRY_LIST_POSITION.md`.
The active mode remains the cross-file invariants / divergence-class sweep.
This session closed **FINDING-024**, the persistence leg of the class-13 object
ordering divergence: DB save/load discarded the relative carry-list position of
equipped objects.

## Outcome

### FINDING-024 — save/load preserves equipped-item carry-list position — ✅ RESOLVED

- **Python**: `mud/db/serializers.py:ObjectSave`, `_serialize_object`,
  `_deserialize_object`; `mud/models/character.py:from_orm`
- **ROM C**: `src/save.c:fwrite_obj` / `fread_obj` writes equipped objects inline
  in `ch->carrying` with `wear_loc`, so the pfile round-trip preserves carry-list
  order for free.
- **Gap**: Python split inventory and equipment into separate JSON blobs. The
  runtime FINDING-020 fix used `Object._carry_seq` to preserve equip→remove
  position, but `_carry_seq` was not saved, so a reloaded equipped object fell
  through `_remove_obj`'s tail fallback when removed.
- **Fix**: added `ObjectSave.carry_seq`; `_serialize_object` writes
  `Object._carry_seq`; `_deserialize_object` restores it; `from_orm` advances
  the global carry-sequence counter past the highest restored value so future
  acquisitions sort newer than loaded objects.
- **Regression**:
  `tests/integration/test_db_canonical_round_trip.py::test_db_round_trip_preserves_equipped_item_carry_position_after_remove`.
  Scenario: bag acquired first, sword acquired/equipped second, jacket acquired
  later; after DB save/load, removing the sword produces `[3045, 3021, 3032]`,
  matching ROM's inline carry-list order.

## Files Modified

- `mud/db/serializers.py`
- `mud/models/character.py`
- `tests/integration/test_db_canonical_round_trip.py`
- `tools/diff_harness/FINDINGS.md`
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
- `CHANGELOG.md`
- `pyproject.toml`

## Test Status

- Focused regression: `pytest -n0 tests/integration/test_db_canonical_round_trip.py::test_db_round_trip_preserves_equipped_item_carry_position_after_remove -q` → passing
- DB round-trip slice: `pytest -n0 tests/integration/test_db_canonical_round_trip.py -q` → passing
- Targeted final slice: `PYTHONPATH=. pytest -n0 tests/integration/test_db_canonical_round_trip.py tests/integration/test_finding020_equip_remove_carry_position.py -q` → 11 passed
- `ruff check .` → clean
- `ruff format --check mud/db/serializers.py mud/models/character.py tests/integration/test_db_canonical_round_trip.py` → already formatted
- `gitnexus_detect_changes(scope=unstaged)` → risk low, no affected processes

## Next Steps

1. **FINDING-025** — probe `MobInstance.equip`: it keeps equipped items in
   `inventory` + `wear_loc` and never populates the equipment dict. Verify mob
   disarm/remove position and whether the missing dict entry is a real divergence.
2. Continue Phase C deterministic diff-harness widening (light hold, money/shop
   paths); add RNG-locked combat only after seed alignment is proven.
