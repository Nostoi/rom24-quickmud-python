# Session Status — 2026-06-10 — FINDING-033 COMM_COMBINE fix (2.13.65)

## Current State

- **Active mode**: cross-file invariants pass + diff-harness coverage expansion
- **Last completed**:
  - **FINDING-033 resolved** — `drive_python_replay` now sets `char.comm =
    CommFlag.COMBINE | CommFlag.PROMPT`, mirroring `diffmain.c:462`. Python
    `show_list_to_char` was already correct; only the harness test-character
    setup was missing the flag.
  - **Hypothesis state-machine test fully green** — `test_generated_no_rng_sequences_match_live_c`
    `xfail` removed; 44 diff-harness tests passing, 0 xfailed.
  - New enforcement test: `test_drive_python_replay_comm_combine_groups_identical_room_objects`
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_FINDING033_COMM_COMBINE_FIX.md](SESSION_SUMMARY_2026-06-10_FINDING033_COMM_COMBINE_FIX.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.65 |
| Tests | 5507 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 26 scenarios, 44 C-oracle tests passing, 0 skipped, 0 xfailed |
| FINDINGS.md highest ID | FINDING-033 (✅ RESOLVED — all findings resolved) |

## Next Intended Task

Cross-file invariants remains the active pass. All known open findings are resolved.
Concrete candidates for the next session:

1. **`drink`/`eat`/`food` consumption diff-harness scenario** — condition decay +
   THIRST/FULL/HUNGER bitvectors. `pyreplay.py` already has `__cond_full=` and
   `__cond_thirst=` meta-commands; `diffmain.c` needs them added (following the
   pattern of existing meta-command handlers) to capture the C golden. No current
   diff-harness coverage for the condition system.

2. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
