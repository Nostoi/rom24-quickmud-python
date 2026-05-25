# Session Status — 2026-05-25 — INV-014 OBJECT-REGISTRY-MEMBERSHIP locked in

## Current State

- **Active pass**: cross-file invariants — backstop for per-file audits.
- **Last completed**: INV-014 OBJECT-REGISTRY-MEMBERSHIP added to
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` with an 8-test
  enforcement suite. ROM `src/db.c:create_object` appends every fresh
  `OBJ_DATA` to the global `object_list` unconditionally; previously
  only `mud/spawning/obj_spawner.py:spawn_object` did so in Python.
  Six production sites built `Object` instances without registering,
  leaving freshly-created corpses, gore objects, money piles, shop
  clones, and DB-restored inventory invisible to `locate object`.
  Added `mud.models.object.create_object(prototype, *, instance_id=None)`
  as the canonical factory; routed every production site through it.
  `mud/skills/handlers.py:_iterate_world_objects` now walks
  `object_registry` first (computing the holder per ROM
  `src/magic.c:3747`) and falls back to a room/character walk as a
  compat backstop for legacy unit tests. Surfaced symptom that opened
  this thread: an object spawned but not yet placed
  (`in_room=None, carried_by=None, in_obj=None`) was skipped by locate;
  ROM reports it as "one is in somewhere". Version bumped 2.9.2 → 2.9.3.
- **Pointer to latest summary**: see CHANGELOG entry [2.9.3] and
  tracker row INV-014 for the durable record (no separate
  `SESSION_SUMMARY_*.md` written for this single-cluster session).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.3 |
| Tests | 4703 passed, 4 skipped, 0 failed |
| Cross-file invariants | 14 of ~20 budget; INV-001 … INV-014 all ✅ ENFORCED |
| Branch | `master` (local — not yet pushed) |
| Watch list | Empty. |

## Next Intended Task

Watch list is empty. Plausible next directions (user's call):

1. **End-to-end coverage for INV-012 newly-live systems** — still on
   the table: mobprog `oload` triggers, full decay loop. (The
   `locate object` slice was completed as INV-014 above.) Each is
   *new* coverage, not regression closure.
2. **Pick the next ⚠️ Partial / ❌ Not Audited row from
   `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`** — note the tracker
   shows 0 Partial / 0 Not Audited in P0/P1/P2 and only ✅ entries in
   P3; default audit path is exhausted for now.
3. **Optional Phase 2 cosmetic sweep** — `prototype` → `pIndexData`
   (~291 refs) and `contained_items` → `contains` (~182 refs). Backlog
   note at `docs/parity/PHASE_2_ROM_NAME_SWEEP_OPTIONAL.md` explains
   why this is deferred.
4. **Surface a new INV candidate** — if a real bug crosses module
   boundaries during normal audit work, file the next free INV row.

## Push gate

Local v2.9.3 commit pending push. CHANGELOG and tracker rows updated.
Awaiting per-cluster push approval per AGENTS.md.
