# Session Status — 2026-06-14 — act_obj.c entry-gate sweep (RECITE-006)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). Following the "category-error" lead — a precondition checked in the
  wrong order or **borrowed from the wrong command family**, where the *first
  failing gate selects the message* (SHOUT-005, TELL-009, GIVE-003 shape) —
  through the `magic_items.py` magic-item verbs.
- **Last completed**:
  - **RECITE-006** — `do_recite` borrowed empty-arg gate. Python opened with
    `if not arg1: return "What do you want to recite?"`, a gate ROM `do_recite`
    (`src/act_obj.c:1910-1974`) does **not** have — it was borrowed from the
    sibling `do_quaff`'s "Quaff what?". ROM goes straight to `get_obj_carry`;
    with an empty arg `is_name("")` is FALSE (`src/handler.c:942-943`), so the
    lookup returns NULL → "You do not have that scroll." Removed the borrowed
    gate. The prior-session "is_name('')==TRUE first-match" hypothesis was
    overturned by re-reading the C — no `get_obj_carry`/`is_name` change needed.
    (v2.14.99)
  - **do_brandish / do_zap** verified gate-order **clean** (no change) —
    sequences match ROM `src/act_obj.c:1978-2064` / `:2068-2157` in presence +
    order.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_ACT_OBJ_RECITE006.md](SESSION_SUMMARY_2026-06-14_ACT_OBJ_RECITE006.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.99 |
| Tests | 5788 passed / 4 skipped |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | act_obj.c entry-gate sweep (RECITE-006 closed); cross-file / divergence-class pass continues |

## Next Intended Task

The act_obj.c entry-gate sweep across get/give/drop/put/recite/brandish/zap has
now closed GIVE-003 + RECITE-006 with everything else verified clean — this verb
family's borrowed-gate surface looks exhausted. Continuing the "category-error"
lead, the next untouched candidates are the **position/condition gate families**
elsewhere (`act_move.c` / `fight.c` entry gates), though those are mostly
single-gate sites (low borrowing surface for this class). Alternatively, per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md`, the explicitly-named open lever with
higher expected yield is the **Hypothesis state-machine → diff_harness widening**
(Class 11/Phase C), which is enumeration-independent (guardrail 3) and where most
recent FINDING-0xx originated.
