# Session Status — 2026-06-09 — harness keyed-door rules (2.13.37)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Hypothesis keyed-door widening added.**
    `DeterministicNoRngDiffMachine` now exercises Midgaard Cityguard HQ's stock
    keyed west door (`close`, `lock`, `unlock`, `pick`) against the live ROM C
    oracle.
  - Diff-harness `__goto=<vnum>` and `__level=<n>` meta-commands added to both
    `src/diff_shim/diffmain.c` and `tools/diff_harness/pyreplay.py`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_HARNESS_KEYED_DOOR_RULES.md](SESSION_SUMMARY_2026-06-09_HARNESS_KEYED_DOOR_RULES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.37 |
| Tests | 5461 passed, 5 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 18 generated-oracle tests |
| Class 11 dynamic widening | Keyed-door rules added |

## Next Intended Task

**Remaining cross-file invariant candidates:**

1. **Hypothesis state machine widening** (Class 11 Phase C, ongoing): add
   another deterministic command/watch-set surface to
   `DeterministicNoRngDiffMachine` in `tools/diff_harness/generated.py`.
2. **`nuke_pets` lifecycle**: probe whether Python correctly extracts charmed
   followers on their master's death/extract (`src/handler.c:nuke_pets`).
3. **`TRIG_ENTRY` call-site coverage**: verify `mp_greet_trigger` fires when a
   mob enters a room — currently wired in `mud/world/movement.py` but not
   confirmed against all entry paths.
