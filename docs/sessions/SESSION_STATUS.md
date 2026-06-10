# Session Status — 2026-06-10 — FINDINGS.md numbering cleanup (2.13.61)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **FINDINGS.md documentation cleanup** — reconciled three accumulated numbering
    errors in `tools/diff_harness/FINDINGS.md`:
    - FINDING-026 (room-occupant look-order, 2026-06-09) → renamed to **FINDING-031**
      (was filed after FINDING-030 was the max; collided with existing FINDING-026)
    - FINDING-024 (class-13 bypass sweep) → renamed to **FINDING-032** (collided
      with FINDING-024 save/load carry-seq)
    - Stale ⚠️ OPEN block (orphaned FINDING-022 pre-resolution text) removed from
      FINDING-032's entry
  - **INV-015 AFFECT-EXPIRY-LIFECYCLE sub-contracts locked (2.13.61)** — prior
    session: two enforcement tests added for RNG-slot ordering (GL-026) and
    msg_off dedup.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_FINDINGS_MD_NUMBERING_CLEANUP.md](SESSION_SUMMARY_2026-06-10_FINDINGS_MD_NUMBERING_CLEANUP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.61 |
| Tests | 5500 passed, 5 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 22 scenarios, 38 passing |
| FINDINGS.md highest ID | FINDING-032 |

## Next Intended Task

Cross-file invariants remains the active pass. Both candidates from the prior
SESSION_STATUS.md were confirmed already resolved. Two concrete next steps:

1. **New diff-harness scenario** — author a scenario for an untested surface:
   charm/follower wear-off lifecycle, sanctuary+haste affect bitvectors with tick
   expiry, or drink/eat/food consumption. Drop a `tools/diff_harness/scenarios/<name>.json`
   and the smoke test auto-skips until a golden is captured. This is the most
   enumeration-independent way to surface new parity gaps.

2. **MATH-002/003/004** — documented ⚠️ OPEN hygiene items (LOW severity) in
   `docs/parity/audits/MATH_AND_RNG.md`. No observable behavioral gap; held for a
   future PARITY008 lint rule. Close only if a new session wants clean-slate
   hygiene.
