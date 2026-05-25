# Session Status — 2026-05-25 — INV-014 + INV-013 carrier-field sweep (2.9.6)

## Current State

- **Active pass**: cross-file invariants — INV-012's downstream
  coverage cycle (locate, mpoload, equip/remove symmetry, decay
  loop) sealed. Natural stopping point.
- **Last completed**: four sequential clusters across 2.9.3 → 2.9.6:
  - **2.9.6** — end-to-end decay-loop coverage for INV-012/13/14.
  - **2.9.5** — `Character.equip_object` / `remove_object` carrier-
    field symmetry (INV-013).
  - **2.9.4** — `Character.add_object` + `do_mpoload` reinforcement
    (INV-013 + INV-011).
  - **2.9.3** — new invariant INV-014 OBJECT-REGISTRY-MEMBERSHIP
    locked in; every Python `Object(...)` construction routed through
    `mud.models.object.create_object`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-25_INV014_AND_INV013_OBJECT_REGISTRY_SWEEP.md](SESSION_SUMMARY_2026-05-25_INV014_AND_INV013_OBJECT_REGISTRY_SWEEP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.6 |
| Tests | 4712 passed, 4 skipped, 0 failed |
| Cross-file invariants | 14 of ~20 budget; INV-001 … INV-014 all ✅ ENFORCED |
| Branch | `master` (synced with `origin/master`; `v2.9.3` – `v2.9.6` tags published) |
| Watch list | Empty. |

## Next Intended Task

The default audit path is exhausted (zero Partial / Not Audited rows
in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`) and the cross-
file invariants watch list is empty. Options for the next session:

1. **Phase 2 cosmetic sweep** — `prototype` → `pIndexData`
   (~291 refs) and `contained_items` → `contains` (~182 refs).
   Backlog note at `docs/parity/PHASE_2_ROM_NAME_SWEEP_OPTIONAL.md`
   explains why this is deferred (low gameplay value); the dataclass
   `@property` aliases are already in place to make it mechanical.
2. **Wait for an organic cross-module bug to file as INV-015.** The
   probe-then-scope pattern has been productive — wait for the next
   real divergence to surface, then file as the next free INV row.
3. **Revisit a 95%-audited file with known user-visible drift** if
   one comes up during normal gameplay testing.

No specific gap currently calling for attention.
