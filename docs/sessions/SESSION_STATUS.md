# Session Status — 2026-06-09 — FINDING-026 room people order (2.13.39)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **`FINDING-026` resolved.** `Room.add_mob` now head-inserts into
    `room.people`, matching ROM `char_to_room` for reset-spawned NPCs.
  - **Keyed-door traversal landed.** The generated keyed-door live C replay now
    goes `west` into Captain's Office and `east` back to Cityguard HQ after
    `open west`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_FINDING026_ROOM_PEOPLE_ORDER.md](SESSION_SUMMARY_2026-06-09_FINDING026_ROOM_PEOPLE_ORDER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.39 |
| Tests | 5462 passed, 5 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 18 generated-oracle tests |
| Class 11 dynamic widening | Keyed-door traversal added; FINDING-026 resolved |

## Next Intended Task

Continue Class 11 / Phase C dynamic differential widening on another
deterministic command/watch-set surface. Current candidates: `nuke_pets`
lifecycle probing (`src/handler.c:nuke_pets`) or `TRIG_ENTRY` call-site coverage
for mob entry paths. Start by reading the ROM C contract and then add one
focused failing test before changing Python behavior.
