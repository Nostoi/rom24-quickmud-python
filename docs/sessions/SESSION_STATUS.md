# Session Status — 2026-06-03 — FINDING-020 carry-list position (2.13.6)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **FINDING-020 — equip→remove carry-list position** ✅ RESOLVED (PC path,
    2.13.6). ROM keeps equipped objects in `ch->carrying` (only `wear_loc`
    flips), so a removed item keeps its original LIFO slot. C oracle confirmed
    the position is *relative to acquisition order*, not a fixed index. Fixed via
    an `Object._carry_seq` acquisition-sequence shim; `_remove_obj` re-inserts by
    descending seq. Validated against the live C oracle (6 scenarios) + un-gated
    diff-harness generated remove rules. 3 new integration tests.
  - Room-contents `look()` `show_list_to_char` parity (2.13.5).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_FINDING_020_CARRY_LIST_POSITION.md](SESSION_SUMMARY_2026-06-03_FINDING_020_CARRY_LIST_POSITION.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.6 |
| Tests | Full suite `pytest` → **5417 passed, 4 skipped**; `ruff check .` clean |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Divergence class 13 | object-list ordering — runtime legs closed (INV-039 + FINDING-020) |
| Open engine findings | FINDING-024 (save/load order), FINDING-025 (mob equip model) |

## Next Intended Task

1. **FINDING-024** — save/load persistence leg of the carry-list ordering
   divergence: `equipment_state` (dict) carries no position relative to the
   ordered `inventory_state`, and `_carry_seq` is not persisted, so a reloaded-
   then-removed item appends. Persist `_carry_seq` or restore the carry list
   inline; needs a diff-harness save/reload scenario or a focused persistence test.
2. **FINDING-025** — probe `MobInstance.equip`: it keeps equipped items in
   `inventory` + `wear_loc` and never populates the equipment dict (different
   model from PCs). Verify mob disarm position and whether the missing dict entry
   is a real divergence. ROM uses one carry-list+`wear_loc` model for both.
3. Continue Phase C deterministic diff-harness widening (light hold, money/shop
   paths); add RNG-locked combat only after seed alignment is proven.

## Other open / deferred items

- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.
