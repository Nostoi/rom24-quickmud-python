# Session Status — 2026-05-25 — INV-013 OBJECT-LOCATION-COHERENCE locked in

## Current State

- **Active pass**: cross-file invariants — backstop for per-file audits.
- **Last completed**: INV-013 OBJECT-LOCATION-COHERENCE added to
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` with a 7-test
  enforcement suite. `Object.location` is no longer a stored field —
  it's a property dispatching to the three canonical ROM container
  fields (`in_room`, `carried_by`, `in_obj`) per `src/handler.c:1626
  obj_to_char` / `1953 obj_to_room` / `1968 obj_to_obj`. Two latent
  bugs surfaced and fixed in the conversion (`MobInstance.add_to_inventory`
  cleared carried_by; `make_corpse` left money's `in_obj` unset).
  Version bumped 2.9.1 → 2.9.2.
- **Same-day prior passes**:
  - `test_wait_and_daze_decrement_on_violence_pulse` fix — match ROM
    descriptor path (2.9.1)
  - End-to-end INV-012 ostat-finds-remote-object coverage (no version
    bump)
- **Prior-day arc (2026-05-24)**:
  - INV-010 ROOM-PEOPLE-COHERENCE + dual-`room_registry` fix (2.8.78)
  - INV-011 CARRY-WEIGHT-COHERENCE + `_extract_obj` counter sync (2.8.79)
  - INV-012 OBJECT-LIST-CANONICAL — dual `Object`/`ObjectData`
    consolidation (2.9.0)
- **Pointer to latest summary**: see latest `docs/sessions/SESSION_SUMMARY_*.md`
  (a dedicated 2.9.2 summary has not been written — the changelog
  entries and tracker rows are the durable record).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.2 |
| Tests | 4695 passed, 4 skipped, 0 failed |
| Cross-file invariants | 13 of ~20 budget; INV-001 … INV-013 all ✅ ENFORCED |
| Branch | `master` (up to date with origin/master); `inv-013-object-location-coherence` retained for reference |
| Watch list | Empty. |

## Next Intended Task

Watch list is empty. Plausible next directions (user's call):

1. **Pick the next ⚠️ Partial / ❌ Not Audited row from
   `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`** and run
   `/rom-parity-audit` on it. This is the default mode when there's
   no specific cross-file thread to pull.
2. **End-to-end coverage for newly-live systems from INV-012** —
   locate-object spell, mobprog oload triggers, full decay loop. Each
   is *new* coverage, not regression closure.
3. **Optional Phase 2 cosmetic sweep** — `prototype` → `pIndexData`
   (~291 refs) and `contained_items` → `contains` (~182 refs). Backlog
   note at `docs/parity/PHASE_2_ROM_NAME_SWEEP_OPTIONAL.md` explains
   why this is deferred.
4. **Surface a new INV candidate** — if a real bug crosses module
   boundaries during normal audit work, file the next free INV row.

## Push gate

Nothing local pending push. Master and `v2.9.2` tag both at
`origin/master`. The branch `inv-013-object-location-coherence` is
retained locally — safe to delete once you confirm the merge looks
right (`git branch -d inv-013-object-location-coherence`).
