# Session Status — 2026-06-10 — charm lifecycle scenario + CharSnap master field (2.13.64)

## Current State

- **Active mode**: cross-file invariants pass + diff-harness coverage expansion
- **Last completed**:
  - **`shop_sell_keeper_broke`** C-oracle golden captured — diff harness is now
    0 skipped / 42 passing.
  - **`charm_person_lifecycle`** diff-harness scenario authored and live — exercises
    AFF_CHARM expiry confirming `master` survives `affect_remove` (ROM invariant:
    `affect_remove` does NOT call `stop_follower`).
  - **`__charm_mob=<duration>`** meta-command added to diffmain.c and pyreplay.py.
  - **`CharSnap.master`** field added (schema.py, pysnap.py, diffmain.c) —
    backward-compatible.
  - **FINDING-033 documented** — ROM `show_list_to_char` groups identical room objects
    with `( N)` prefix; Python lists each individually. Hypothesis state-machine test
    found the reproducer; marked xfail(strict=False) pending fix.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_CHARM_PERSON_LIFECYCLE_SCENARIO.md](SESSION_SUMMARY_2026-06-10_CHARM_PERSON_LIFECYCLE_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.64 |
| Tests | 5505 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 26 scenarios, 42 passing, 0 skipped |
| FINDINGS.md highest ID | FINDING-033 (⚠️ OPEN) |

## Next Intended Task

Cross-file invariants remains the active pass. The diff-harness now has 26 scenarios /
42 C-oracle tests passing. Concrete candidates for the next session:

1. **FINDING-033 fix** — implement `( N) ...` object grouping in Python `do_look` /
   `show_list_to_char` (ROM `src/act_info.c show_list_to_char`). Now the only barrier
   to a fully-green Hypothesis state-machine run. LOW severity but well-bounded fix.

2. **Author `drink`/`eat`/`food` consumption scenario** — condition decay,
   THIRST/FULL/HUNGER bitvectors. pyreplay.py already has `__cond_full=` and
   `__cond_thirst=` meta-commands; diffmain.c needs them added for a C golden capture.

3. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
