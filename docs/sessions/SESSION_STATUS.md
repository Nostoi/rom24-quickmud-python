# Session Status — 2026-06-02 — MOVE-005 exit-trigger ordering fixed (2.12.81)

## Current State

- **Active mode**: cross-file invariants via **probe-then-scope** under the
  divergence-class completeness lens. This session ran the standing
  **mob-trigger ordering** candidate and closed the one divergence it surfaced.
- **MOVE-005 (exit-trigger ordering) → ✅ FIXED (2.12.81).** ROM
  `src/act_move.c:move_char` fires `mp_exit_trigger(ch, door)` as the **first**
  action after the door-bounds check — before the exit-existence/`can_see_room`
  check, the movement-cost gate, and (Python-only) the encumbrance gate. Python
  fired it only *after* an `exit is None` early return and the encumbrance gate,
  so a PC walking into a wall or while over-encumbered never fired the room's
  TRIG_EXIT program. Fixed by relocating the trigger block to the top of
  `mud/world/movement.py:move_character`. **Cross-file ordering miss the per-file
  audit masked** — `ACT_MOVE_C_AUDIT.md` had marked the trigger ✅ PARITY by
  checking it is *called*, never its *order*; rows corrected.
- **Mob-trigger ordering probe (mostly exhausted):** FIGHT/HPCNT (INV-026),
  ACT (INV-025), KILL/DEATH (combat engine) already enforced; EXIT now closed;
  BRIBE/GIVE verified at the **call-site ordering** dimension (the one that
  caught EXIT): ROM `do_give` does transfer→act→`mp_give_trigger` (object) and
  money-transfer→act→`mp_bribe_trigger`→changer (coins); Python
  `mud/commands/give.py` matches both.
- **MOVE-006 filed (❌ OPEN):** ROM `move_char` has no carry-weight movement
  gate; the Python `"You are too encumbered to move."` early-return is a non-ROM
  divergence pending verification/removal. Audit row ready.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_MOVE005_EXIT_TRIGGER_ORDERING.md](SESSION_SUMMARY_2026-06-02_MOVE005_EXIT_TRIGGER_ORDERING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.81 |
| Tests | 5363 passed, 4 skipped (full run, 221.81s) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 27 rows (INV-034 ✅ ENFORCED) |
| Divergence-class lens | Layer A 4/4 feasible; class 6 (pointer-identity) ✅ FULLY CLOSED |
| Lint | `ruff check` clean on edited files (repo carries pre-existing errors; none introduced) |

## Next Intended Task

Mob-trigger ordering is largely covered. Candidate next passes:

1. **MOVE-006** — verify/remove the non-ROM encumbrance movement gate
   (`mud/world/movement.py:359-362`). Small, self-contained; has an OPEN audit
   row in `ACT_MOVE_C_AUDIT.md` ready to close via `/rom-gap-closer`.
2. **Highest-ceiling (multi-day):** `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
3. **Housekeeping:** INV tracker consolidation (27 rows, past the ~20 soft cap).

> **Push note:** `origin/master` is at `6b2fbd2b` (2.12.80). This session's
> commits — `8681630c` (MOVE-005, 2.12.81) plus the docs follow-up — are
> **unpushed**. CHANGELOG/version reflect 2.12.81.
