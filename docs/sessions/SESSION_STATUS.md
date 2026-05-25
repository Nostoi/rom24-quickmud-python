# Session Status — 2026-05-25 — Decay loop end-to-end coverage (2.9.6)

## Current State

- **Active pass**: cross-file invariants — closing the INV-012
  newly-live-systems coverage holes that the per-file audits leave.
- **Last completed (2.9.6)**: end-to-end decay-loop coverage for
  INV-012 / INV-013 / INV-014. Three new integration tests in
  `tests/integration/test_decay_loop_inv012.py` pin the
  registry / carrier / carry-counter contracts as they cross the
  `obj_update` → `_extract_obj` boundary:
  - Carried potion timer expiry → off `object_registry`, off
    inventory, carry counters drop.
  - NPC corpse + nested pouch + gem: decay recurses (ROM
    `src/handler.c:2063-2067 extract_obj`) — all three leave the
    registry.
  - Downstream INV-014: decayed obj is no longer findable via
    `locate object`.
  - No production code changed — pure new coverage. Verified no
    regressions in any of the surfaces touched in 2.9.3-2.9.5.
- **Prior clusters this session**:
  - 2.9.5 — INV-013 equip/remove carrier-field symmetry.
  - 2.9.4 — INV-013/INV-011 `Character.add_object` + `do_mpoload`.
  - 2.9.3 — INV-014 OBJECT-REGISTRY-MEMBERSHIP.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.6 |
| Tests | 4712 passed, 4 skipped, 0 failed |
| Cross-file invariants | 14 of ~20 budget; INV-001 … INV-014 all ✅ ENFORCED |
| Branch | `master` (v2.9.3/4/5 pushed; v2.9.6 commit local) |
| Watch list | Empty. |

## Next Intended Task

INV-012's downstream coverage cycle (locate, mpoload, equip/remove
symmetry, decay loop) is now sealed. Plausible next directions
(user's call):

1. **Wrap session** — four solid clusters in one session is well past
   a natural stopping point. SESSION_STATUS / CHANGELOG / tracker
   trails all current.
2. **Phase 2 cosmetic sweep** — `prototype` → `pIndexData`
   (~291 refs) and `contained_items` → `contains` (~182 refs). Backlog
   note at `docs/parity/PHASE_2_ROM_NAME_SWEEP_OPTIONAL.md`.
3. **Surface a new INV candidate** — if a real bug crosses module
   boundaries during normal audit work, file the next free INV row.
4. **Run a `/rom-session-handoff`** to write the canonical session
   summary doc capturing the 2.9.3 → 2.9.6 arc.

## Push gate

Local v2.9.6 commit pending push. v2.9.3-2.9.5 are on origin.
Awaiting per-cluster push approval per AGENTS.md.
