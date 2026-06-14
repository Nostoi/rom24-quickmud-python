# Session Status — 2026-06-14 — act_obj.c entry-gate sweep (GIVE-003)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). Following the act_comm.c "category-error" lead into **act_obj.c
  entry gates** — a precondition checked in the wrong order or borrowed from the
  wrong command family, where the *first failing gate selects the message*
  (SHOUT-005, TELL-009 shape).
- **Last completed**:
  - **GIVE-003** — `_give_money` money-path gate-ordering inversion. ROM
    `do_give` (`src/act_obj.c:682-698`) validates *amount + currency* first
    ("Sorry, you can't do that.") then checks for a missing recipient ("Give
    what to whom?"); Python collapsed both into a missing-victim-first guard, so
    `give 3 copper` / `give 0 gold` (bad currency / non-positive amount, no
    victim) returned the wrong message. Reordered to match ROM. (v2.14.98)
  - **do_get / `_get_obj`** and **do_drop** verified parity-clean (no change) —
    gate sequences match ROM in presence + order. do_drop's money branch reads
    the currency token before validating, so it does NOT share GIVE-003's
    inversion.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_ACT_OBJ_GIVE003.md](SESSION_SUMMARY_2026-06-14_ACT_OBJ_GIVE003.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.98 |
| Tests | 5787 passed / 4 skipped |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | act_obj.c entry-gate sweep (GIVE-003 closed); cross-file / divergence-class pass continues |

## Next Intended Task

The act_obj.c entry-gate probe covered get/give/drop this pass (do_put read clean
against ROM `:357-489` but not locked with a fresh test). Continuing the
"category-error" lead, the next untouched candidates are the **position/condition
gate families** in `consumption.py` (do_eat/do_drink/do_quaff — ROM gates on item
type + hunger/thirst + position). Alternatively, per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md`, the explicitly-named open lever is the
**Hypothesis state-machine → diff_harness widening** (Class 11/Phase C), which is
enumeration-independent (guardrail 3) and where most recent FINDING-0xx
originated — higher expected yield than another hand-picked verb probe.
