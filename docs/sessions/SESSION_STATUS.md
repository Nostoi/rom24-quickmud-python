# Session Status — 2026-06-09 — harness keyed-door open (2.13.38)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Hypothesis keyed-door open widening added.**
    `DeterministicNoRngDiffMachine` now exercises `open west` after the Midgaard
    Cityguard HQ keyed-door close/lock/unlock/pick cycle.
  - **FINDING-026 filed.** A traversal probe into Captain's Office exposed room
    occupant look-order drift (ROM cityguards before captain; Python captain
    before cityguards), so traversal rules were not landed.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_HARNESS_KEYED_DOOR_OPEN.md](SESSION_SUMMARY_2026-06-09_HARNESS_KEYED_DOOR_OPEN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.38 |
| Tests | 5461 passed, 5 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 18 generated-oracle tests |
| Class 11 dynamic widening | Keyed-door open added; FINDING-026 filed |

## Next Intended Task

**Remaining cross-file invariant candidates:**

1. **Hypothesis state machine widening** (Class 11 Phase C, ongoing): add
   another deterministic command/watch-set surface to
   `DeterministicNoRngDiffMachine` in `tools/diff_harness/generated.py`.
2. **`FINDING-026` occupant order**: scope ROM `char_to_room` / reset insertion
   ordering against Python reset/mob placement before landing keyed-door
   traversal rules.
3. **`nuke_pets` lifecycle**: probe whether Python correctly extracts charmed
   followers on their master's death/extract (`src/handler.c:nuke_pets`).
4. **`TRIG_ENTRY` call-site coverage**: verify `mp_greet_trigger` fires when a
   mob enters a room — currently wired in `mud/world/movement.py` but not
   confirmed against all entry paths.
