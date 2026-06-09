# Session Status — 2026-06-09 — ENTER-019 portal followers (2.13.40)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **`ENTER-019` resolved.** Portal followers no longer inherit the
    directional follower `can_see_room` pre-gate. Directional movement still
    requires destination visibility per ROM `act_move.c:218`; portal movement
    now attempts recursive `do_enter` first, matching `act_enter.c:177-198`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_ENTER019_PORTAL_FOLLOWERS.md](SESSION_SUMMARY_2026-06-09_ENTER019_PORTAL_FOLLOWERS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.40 |
| Tests | 5463 passed, 5 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 18 generated-oracle tests |
| Class 11 dynamic widening | ENTER-019 portal follower visibility probe resolved |

## Next Intended Task

Continue Class 11 / Phase C dynamic differential widening on another
deterministic command/watch-set surface. Prefer `TRIG_ENTRY` ordering coverage
for mob entry paths or another source-read lifecycle probe with a concrete
observable; `nuke_pets` already has substantial INV-020/INV-025 coverage, so
avoid duplicating it unless the ROM/Python read exposes a specific missing
contract.
