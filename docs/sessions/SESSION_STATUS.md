# Session Status — 2026-05-28 — FIGHT-020 `kill` single-delivery (FINDING-008 sub-issue 3, re-triaged)

## Current State

- **Active mode**: differential-harness-driven parity verification. This session
  re-triaged FINDING-008 sub-issue 3 (combat line emitted twice at `kill drunk`),
  which the prior session had recorded as a "harness capture artifact." It is a
  **real engine bug** — closed as FIGHT-020 on `master`.
- **Last completed**:
  - **`FIGHT-020`** ✅ FIXED (master 2.11.5, `d1e60112`) — `do_kill` returned
    `multi_hit(...)[0]`, the attacker combat line `apply_damage` had already
    pushed via `_push_message`; the connection loop sends the return value AND
    drains the push, so connected PCs received every `kill`-initiated combat line
    **twice** (SINGLE-DELIVERY / INV-001 violation). `do_kill` now returns `""`
    (ROM's void `do_kill`); combat output flows solely through `_push_message`.
    Also retired a non-ROM `"You kill X."` line. Proven end-to-end with a
    mock-connection delivery harness; 11 combat tests re-baselined.
  - **Re-triage correction**: the FIGHT-019 session's "harness capture artifact"
    triage of sub-issue 3 was **wrong** (it traced only `multi_hit`'s return, not
    the connected-PC push+return double-channel). Master-side docs reconciled;
    `FINDINGS.md` on `diff-harness` still needs the correction.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_FIGHT_020_KILL_SINGLE_DELIVERY.md](SESSION_SUMMARY_2026-05-28_FIGHT_020_KILL_SINGLE_DELIVERY.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-28_FIGHT_019_THAC0_HIT_MODEL.md](SESSION_SUMMARY_2026-05-28_FIGHT_019_THAC0_HIT_MODEL.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version (master) | **2.11.5** (1 commit ahead of `origin/master` — `d1e60112`, **UNPUSHED**). `diff-harness` separate, unmerged. |
| Tests (master) | **4930 passed, 4 skipped, 0 failed** (full parallel suite, post-FIGHT-020). |
| ROM C files audited | 40 / 43 ✅ (3 N/A). `fight.c` row: FIGHT-019 (hit model) + FIGHT-020 (`do_kill` single-delivery) closed. |
| Differential harness | **Sound.** Surfaced FINDING-001→008. FINDING-008 sub-issue 1 (FIGHT-019) + sub-issue 3 (FIGHT-020) now resolved on `master`; sub-issue 2 (color norm) remains harness-side. `combat_melee_rounds` xfail stays red until `diff-harness` picks up master + sub-issue 2. v1 on `diff-harness`, unmerged. |
| INV-001 follow-ups | **2 open** (same SINGLE-DELIVERY contract): (a) `broadcast_room`/`broadcast_global` dual-channel; (b) `do_surrender` return-value double-send. Both filed under INV-001. |

## Next Intended Task

1. **Merge `master` → `diff-harness`** — brings FIGHT-019 + FIGHT-020 onto the
   harness branch (resolves FINDING-008 sub-issues 1 + 3 there).
2. **On `diff-harness`: fix sub-issue 2** (color normalization — strip ROM `{`
   tokens in `compare._normalize_output`, reuse `mud.net.ansi.strip_ansi`) and
   **correct `tools/diff_harness/FINDINGS.md`** (sub-issue 3 → "real engine bug,
   FIGHT-020", not "capture artifact").
3. **Re-run `combat_melee_rounds`** — the drunk (31 HP) does not die at step 4, so
   the `broadcast_room` death duplicate won't affect it; expect step 4 to clear,
   but the first divergence may **advance to step 5**. Re-run, don't declare. Then
   merge `diff-harness` → `master`.
4. **Close INV-001 follow-ups** (a) `broadcast_room` and (b) `do_surrender` as
   separate failing-test-first gap-closer commits.
5. **Combat-test brittleness** — pin `number_bits` in the unseeded
   `tests/test_combat.py` hit/damage tests (single-file `-n0` runs are RNG-fragile;
   the canonical parallel suite is green). Candidate hardening pass; see
   `FIGHT_C_AUDIT.md` Notes.
