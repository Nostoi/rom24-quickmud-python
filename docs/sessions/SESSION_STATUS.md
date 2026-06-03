# Session Status — 2026-06-03 — INV-037 follow self pet-pointer cleanup (2.12.85)

## Current State

- **Active mode**: cross-file invariants via **probe-then-scope** under the
  divergence-class completeness lens.
- **INV-037 (follow self pet-pointer cleanup) → ✅ ENFORCED (2.12.85).**
  ROM `src/act_comm.c:1562-1570 do_follow` delegates `follow self` to
  `stop_follower(ch)`, and `src/act_comm.c:1631-1632 stop_follower` clears
  `ch->master->pet` when it points at `ch`. Python's command-path
  `mud.commands.group_commands.stop_follower` now clears the stale owner pet
  pointer before detaching `master`/`leader`.
- **Production divergence closed**: `follow self` could leave `master.pet`
  pointing at a detached follower.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_INV037_FOLLOW_SELF_PET_POINTER.md](SESSION_SUMMARY_2026-06-03_INV037_FOLLOW_SELF_PET_POINTER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.85 |
| Tests | `pytest -n0 tests/integration/test_inv037_follow_self_pet_pointer_cleanup.py tests/integration/test_act_comm001_follow_self_single_message.py tests/integration/test_act_comm002_follow_other_single_message.py tests/integration/test_do_follow_master_notification.py tests/integration/test_follow_can_see_gating.py -q` → 8 passed |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 30 active rows (INV-037 ✅ ENFORCED) |
| Divergence-class lens | Layer A 4/4 feasible; class 6 (pointer-identity) ✅ FULLY CLOSED |
| Lint / impact | `ruff check mud/models/character.py mud/commands/group_commands.py tests/integration/test_inv036_sleep_strip_on_combat_start.py tests/integration/test_inv037_follow_self_pet_pointer_cleanup.py` clean; `gitnexus_impact(stop_follower, mud/commands/group_commands.py)` LOW risk; GitNexus detect_changes LOW risk, 0 affected processes |

## Next Intended Task

Candidate next passes:

1. **Highest-ceiling (multi-day):** `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
2. **New cross-INV probe area** — affect ticks or another group/follower-chain
   edge.
3. **Housekeeping:** INV tracker consolidation (30 active rows, past the ~20
   soft cap).
