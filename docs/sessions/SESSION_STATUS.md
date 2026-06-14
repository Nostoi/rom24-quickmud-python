# Session Status — 2026-06-14 — fight.c do_kill charm-order (FIGHT-074)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). Following the "category-error / borrowed-gate" lead — a precondition
  checked in the wrong order, **borrowed from the wrong command family, or omitted
  relative to a sibling**, where the *first failing gate selects the player-facing
  message* (SHOUT-005, TELL-009, GIVE-003, RECITE-006, FIGHT-067/069/071 shape)
  — in the `fight.c` offensive-skill **entry gates**.
- **Last completed**:
  - **FIGHT-074** — `do_kill` charm gate now checked LAST (after is_safe +
    kill-steal), matching ROM `src/fight.c:2794-2807` order. Removed the
    `include_charm` param and the charm branch from `_kill_safety_message`
    entirely (it is now a pure ROM `is_safe()` mirror); all three offensive verbs
    (kill/dirt/trip) carry their own charm gate at the ROM-specified position.
    Completes the kill/dirt/trip charm-order trio FIGHT-071 started. (v2.14.103)
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT074_KILL_CHARM_ORDER.md](SESSION_SUMMARY_2026-06-14_FIGHT074_KILL_CHARM_ORDER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.103 |
| Tests | +3 FIGHT-074 (area suite: 294 passed / 1 skipped for `bash or fight or dirt or trip or kill`) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | fight.c offensive-skill entry-gate sweep (FIGHT-067/069/071/074 closed); cross-file / divergence-class pass continues |

## Next Intended Task

Continue the fight.c offensive-skill entry-gate sweep. Open rows in
`docs/parity/FIGHT_C_AUDIT.md`:

- **FIGHT-070** — extract a shared message-emitting `is_safe` so the entry gates
  surface ROM's context lines ("Not in this room.", shopkeeper, pet, …) instead
  of silently swallowing them via the bool `is_safe`. Structural; affects every
  bool-`is_safe` entry gate (do_bash now). Highest-leverage of the remaining rows.
- **FIGHT-072 / FIGHT-073** — do_dirt `victim==ch`-before-BLIND order swap + BLIND
  `$E` pronoun message (MINOR, act()-render class). **FIGHT-068** — analogous
  do_bash `victim==ch`/position order swap.

Beyond this verb family, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the
higher-yield open lever remains the **Hypothesis state-machine → diff_harness
widening** (Class 11 / Phase C), enumeration-independent (guardrail 3), where most
recent FINDING-0xx originated.
