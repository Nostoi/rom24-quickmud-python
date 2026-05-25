# Session Status — 2026-05-24 — INV-012 OBJECT-LIST-CANONICAL locked in

## Current State

- **Active pass**: cross-file invariants — backstop for per-file audits.
- **Last completed**: INV-012 OBJECT-LIST-CANONICAL added to
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` with an 8-test
  enforcement suite. `mud.models.obj.ObjectData` deleted; single
  canonical `Object` runtime class. `object_registry` now populated
  at spawn / drained at extract — locate-object spells, mobprog oload
  triggers, music/object decay all execute against real data for the
  first time. Version bumped 2.8.79 → 2.9.0.
- **Same-day prior passes**:
  - INV-010 ROOM-PEOPLE-COHERENCE + dual-`room_registry` fix (2.8.78)
  - INV-011 CARRY-WEIGHT-COHERENCE + `_extract_obj` counter sync (2.8.79)
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-24_INV012_OBJECT_CONSOLIDATION.md](SESSION_SUMMARY_2026-05-24_INV012_OBJECT_CONSOLIDATION.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.0 |
| Tests | 4686 passed, 1 pre-existing failure (`test_wait_and_daze_decrement_on_violence_pulse`, present on master) |
| Cross-file invariants | 12 of ~20 budget; INV-001 … INV-012 all ✅ ENFORCED |
| Branch | `inv-012-object-consolidation` — 17 implementation commits, local only, awaiting user merge/push decision |
| Active focus | Watch list empty. Followups documented but not active. |

## Next Intended Task

Watch list is empty. Plausible next directions (user's call):

1. **Merge `inv-012-object-consolidation` into master** (after user
   review). Then push origin/master with the consolidated 2.9.0 cut.
2. **`mud/magic/effects.py` `isinstance(target, Object)` cleanup** (5
   tautological filters after the dual-class consolidation; one short
   commit).
3. **End-to-end coverage of newly-live systems** — locate-object spell,
   mobprog oload, full decay loop. Each is *new* coverage, not a
   regression closure. Worth a dedicated test session.
4. **Phase 2 ROM-name field renames** — cosmetic parity polish
   (`prototype` → `pIndexData`, etc. across 71 files). Own session,
   own INV if pursued.
5. **Triage the pre-existing
   `test_wait_and_daze_decrement_on_violence_pulse` failure** still
   on master.

## Push gate

Local commit ready for INV-012 (Task 5 final commit) on the
`inv-012-object-consolidation` branch. Awaiting explicit user
approval to merge to master and push origin/master.
