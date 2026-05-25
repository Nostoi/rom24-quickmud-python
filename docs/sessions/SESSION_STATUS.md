# Session Status — 2026-05-25 — INV-013/INV-011 mpoload reinforcement (2.9.4)

## Current State

- **Active pass**: cross-file invariants — reinforcing existing INV
  enforcement points with newly-surfaced contract gaps.
- **Last completed (2.9.4)**: `Character.add_object` and `do_mpoload`
  pinned to ROM `src/handler.c:1626 obj_to_char`. Two stacked gaps
  closed in one cluster:
  - `Character.add_object` now sets `obj.location = self` after the
    inventory append (INV-013 property dispatch sets `carried_by` and
    clears `in_room` / `in_obj`). Previously left the canonical
    carrier field as `None` for every direct caller.
  - `do_mpoload` (inventory branch) now routes through
    `ch.add_object(obj)` instead of appending directly. Previously
    skipped both INV-013 (`carried_by`) AND INV-011 (`carry_weight` /
    `carry_number`).
  - 3 enforcement tests in
    `tests/integration/test_inv013_add_object_carrier.py`; INV-011 and
    INV-013 "Touched by" trails extended in the tracker.
- **Prior cluster (2.9.3)**: INV-014 OBJECT-REGISTRY-MEMBERSHIP — every
  Python `Object(...)` construction site routed through
  `mud.models.object.create_object`; iterator walks `object_registry`
  first. Symptom: `locate object` could not find homeless or
  newly-created objects (corpses, money, shop clones, DB-restored
  inventory).
- **Pointer to latest summary**: see CHANGELOG entries [2.9.3] +
  [2.9.4] and tracker INV-014 row / INV-011 + INV-013 "Touched by"
  trails for the durable record.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.4 |
| Tests | 4706 passed, 4 skipped, 0 failed |
| Cross-file invariants | 14 of ~20 budget; INV-001 … INV-014 all ✅ ENFORCED |
| Branch | `master` (v2.9.3 pushed; 2.9.4 commit local) |
| Watch list | Empty. |

## Next Intended Task

Watch list is empty. Plausible next directions (user's call):

1. **Audit `Character.equip_object` / `remove_object` for the same
   INV-013 gap.** `add_object` was missing the carrier set; the symmetry
   tests for equip (carried_by must stay set; only `wear_loc` changes)
   and remove (carried_by must clear) were not part of the 2.9.4
   cluster. Worth a focused 30-min sweep.
2. **End-to-end coverage for the remaining INV-012 newly-live system**:
   the corpse/decay loop. Mobprog `oload` is now fully INV-013/INV-011
   compliant; locate-object covered via INV-014.
3. **Phase 2 cosmetic sweep** — `prototype` → `pIndexData`
   (~291 refs) and `contained_items` → `contains` (~182 refs). Backlog
   note at `docs/parity/PHASE_2_ROM_NAME_SWEEP_OPTIONAL.md`.
4. **Surface a new INV candidate** — if a real bug crosses module
   boundaries during normal audit work, file the next free INV row.

## Push gate

Local v2.9.4 commit pending push. v2.9.3 is on origin. Awaiting
per-cluster push approval per AGENTS.md.
