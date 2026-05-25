# Session Status — 2026-05-25 — INV-013 equip/remove symmetry (2.9.5)

## Current State

- **Active pass**: cross-file invariants — INV-013 add/equip/remove
  symmetry sweep.
- **Last completed (2.9.5)**: `Character.equip_object` and
  `Character.remove_object` pinned to ROM `src/handler.c equip_char` /
  `src/handler.c:1642 obj_from_char`:
  - `equip_object` now sets `obj.carried_by = self` (equipped objs
    stay owned by the carrier; only `wear_loc` changes per ROM).
  - `remove_object` now clears `obj.carried_by` (`obj_from_char`
    clears it atomically with extraction). Defensive `getattr` guard
    handles legacy tests passing `SimpleNamespace` stand-ins.
  - 3 new enforcement tests added to
    `tests/integration/test_inv013_add_object_carrier.py` (6 total
    covering the full add / equip / remove cycle).
- **Prior cluster (2.9.4)**: `Character.add_object` sets
  `obj.carried_by`; `do_mpoload` routes through `add_object`. Closes
  the INV-013 + INV-011 stack that surfaced from the INV-012
  follow-up scan.
- **Prior cluster (2.9.3)**: INV-014 OBJECT-REGISTRY-MEMBERSHIP locked
  in. Every Python `Object(...)` construction routes through
  `mud.models.object.create_object`; iterator walks `object_registry`
  first.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.5 |
| Tests | 4709 passed, 4 skipped, 0 failed |
| Cross-file invariants | 14 of ~20 budget; INV-001 … INV-014 all ✅ ENFORCED |
| Branch | `master` (v2.9.3 + v2.9.4 pushed; v2.9.5 commit local) |
| Watch list | Empty. |

## Next Intended Task

INV-013 carrier-field symmetry is now fully enforced for the
add/equip/remove cycle. Plausible next directions (user's call):

1. **End-to-end coverage for the corpse/decay loop** — the remaining
   INV-012 newly-live system not yet covered by INV-013/INV-014 work.
   Specifically: ensure decayed objects extract cleanly from
   `object_registry` and from any carrier inventory.
2. **Phase 2 cosmetic sweep** — `prototype` → `pIndexData`
   (~291 refs) and `contained_items` → `contains` (~182 refs). Backlog
   note at `docs/parity/PHASE_2_ROM_NAME_SWEEP_OPTIONAL.md`.
3. **Surface a new INV candidate** — if a real bug crosses module
   boundaries during normal audit work, file the next free INV row.
4. **Wrap session** — three clusters in one session (INV-014,
   add_object/mpoload, equip/remove symmetry) is a natural stopping
   point.

## Push gate

Local v2.9.5 commit pending push. v2.9.3 and v2.9.4 are on origin.
Awaiting per-cluster push approval per AGENTS.md.
