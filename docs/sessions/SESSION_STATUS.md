# Session Status — 2026-06-02 — MOVE-005 + MOVE-006 (act_move ordering & encumbrance gate) (2.12.82)

## Current State

- **Active mode**: cross-file invariants via **probe-then-scope** under the
  divergence-class completeness lens. This session ran the standing
  **mob-trigger ordering** candidate, closed the one divergence it surfaced
  (MOVE-005), and removed the non-ROM gate that probe exposed (MOVE-006).
- **MOVE-005 (exit-trigger ordering) → ✅ FIXED (2.12.81).** ROM
  `src/act_move.c:move_char` fires `mp_exit_trigger(ch, door)` **first** (after
  the door-bounds check) — before the exit-existence/`can_see_room` check, the
  move-cost gate, and the encumbrance gate. Python fired it after an
  `exit is None` early return and the encumbrance gate, so a PC walking into a
  wall or while over-encumbered never fired the room's TRIG_EXIT program. Fixed
  by relocating the trigger block to the top of `move_character`. Cross-file
  ordering miss the per-file audit masked (✅ PARITY checked *called*, not
  *order*); rows corrected.
- **MOVE-006 (non-ROM encumbrance movement gate) → ✅ FIXED (2.12.82).** ROM
  `move_char` has **no** carry-weight/carry-number movement gate anywhere
  (verified across all of `src/`) — caps are enforced at *pickup* time
  (`do_get`/`do_give`/`wear`), not at movement. The Python
  `"You are too encumbered to move."` early-return was an invention; 5 tests
  asserted it citing `act_move.c:204` (actually the arrival broadcast). Removed
  the gate, **kept** all carry-cap machinery, corrected the 5 tests. **User
  confirmed** the ROM-faithful removal (surfaced via `AskUserQuestion` because it
  changes player-facing behavior).
- **Mob-trigger ordering probe — exhausted:** FIGHT/HPCNT (INV-026), ACT
  (INV-025), KILL/DEATH (combat engine) enforced; EXIT closed (MOVE-005);
  BRIBE/GIVE verified at the call-site ordering dimension (transfer→trigger,
  coins→bribe→changer — `mud/commands/give.py` matches ROM `do_give`).

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_MOVE005_EXIT_TRIGGER_ORDERING.md](SESSION_SUMMARY_2026-06-02_MOVE005_EXIT_TRIGGER_ORDERING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.82 |
| Tests | 5364 passed, 4 skipped (full run, 180.44s) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 27 rows (INV-034 ✅ ENFORCED) |
| Divergence-class lens | Layer A 4/4 feasible; class 6 (pointer-identity) ✅ FULLY CLOSED |
| Lint | `ruff check` clean on edited lines (repo carries pre-existing errors; none introduced) |

## Next Intended Task

Mob-trigger ordering is covered; `act_move.c` movement gates are now ROM-faithful.
Candidate next passes:

1. **Highest-ceiling (multi-day):** `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
2. **New cross-INV probe area** — position-transition edges, affect ticks, or
   mob `TRIG_RANDOM`/`TRIG_DELAY` ordering (`src/update.c:452-458`).
3. **Housekeeping:** INV tracker consolidation (27 rows, past the ~20 soft cap).

> **Push note:** `origin/master` is at `80cbf34d` (2.12.81 — MOVE-005 pushed).
> The MOVE-006 commit `0c890d57` (2.12.82) + this docs follow-up are
> **unpushed**. CHANGELOG/version reflect 2.12.82.
