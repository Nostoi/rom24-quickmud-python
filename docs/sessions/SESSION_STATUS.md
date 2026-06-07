# Session Status — 2026-06-07 — Diff-Harness Phase C Widening: Full Drink + Pour Into Held Container (2.13.17)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness Phase C widening — full drink logic + pour into held container.**
    C shim now supports `__cond_full=`, `__cond_thirst=`, and `__mob_hold=` meta-commands.
    The `drink_bottle_beer` state-machine rule injects `__cond_full=0` before drinking,
    exercising the actual sip-decrement + condition-gains path against the C oracle.
    Added `give_drunk_empty_cup` and `pour_bottle_into_drunk_held_cup` rules exercising
    the vch branch of ROM `do_pour` (`src/act_obj.c:1146-1157`). Fixed snapshot inventory
    filter (`_is_equipped`) to exclude equipped items, matching the C shim.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-07_DRINK_POUR_HELD.md](SESSION_SUMMARY_2026-06-07_DRINK_POUR_HELD.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.17 |
| Tests | 34/34 diff harness suite passing |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 8 static + 14 generated-oracle tests (+1 this session) |
| Generated state machine objects | 8 (7 objects + 1 mob) |
| Generated state machine rules | 42 rules (+4 this session: give_drunk_empty_cup, pour_bottle_into_drunk_held_cup, drink_bottle_beer updated, _drunk_has_empty_cup flag) |

## Next Intended Task

1. Continue cross-INV probe-then-scope as the active pass mode. The liquid/drink
   surface for the deterministic harness (no RNG) is now conformed — pour-out,
   pour-between, drink, and pour-into-character are all exercised against the C
   oracle. Remaining surface areas for diff-harness widening: mob scripts, spell
   casting (requires seed alignment), shop interactions, affect expiration.
