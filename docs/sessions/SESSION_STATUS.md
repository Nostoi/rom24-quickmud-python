# Session Status — 2026-06-19 — diff-harness widening: examine/compare

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). The enumeration-independent lever (`DIVERGENCE_CLASS_ROSTER.md`
  Layer C / Class 13) is widening `tools/diff_harness/` against the live ROM C
  oracle. Class 11 (mobprog) is COMPLETE; this session widened the **non-mobprog
  command** frontier with `examine` and `compare`.
- **Last completed** (this session, 1 commit, master): diff-harness `examine` +
  `compare` coverage. Read-only `examine_*`/`compare_sword_to_jacket` rules on
  `DeterministicNoRngDiffMachine` plus two fixed scenarios
  (`test_generated_examine_object_branches_matches_live_c`,
  `test_generated_compare_objects_matches_live_c`) that deterministically drive
  every branch each run. `do_examine` (ITEM_CONTAINER / ITEM_DRINK_CON / weapon)
  and `do_compare` (mismatch / value / same-object) both **converge against the
  live C oracle on the first pass — no divergence**. Locks the act-rendered
  output incl. ROM's verbatim `"with  a amber liquid"` drink-level wording.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_DIFF_HARNESS_EXAMINE_COMPARE.md](SESSION_SUMMARY_2026-06-19_DIFF_HARNESS_EXAMINE_COMPARE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.134 |
| Tests | 5843 passed, 4 skipped, 0 failed (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep |

## Next Intended Task

Continue non-mobprog command widening of the diff harness (the
enumeration-independent finder). Surveyed-but-not-done deterministic candidates:
container open/close/lock/unlock (do_open/do_close OBJECT branch, distinct from
the door-EXIT branch already covered), `wear all`/`get all`/`drop all` bulk
loops, and `sacrifice` (state-mutating — Class 10 lifecycle; verify whether
`do_sacrifice` draws RNG in `src/act_obj.c` before bracketing). Lower priority:
`mud/entrypoint.py` dead-code cleanup. Guardrail 3 reminder: a clean sweep means
"this known surface is locked," never "close to ROM parity."
