# Session Status — 2026-06-14 — fight.c dirt/trip kill-steal gate (FIGHT-069)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). Following the "category-error / borrowed-gate" lead — a precondition
  checked in the wrong order, **borrowed from the wrong command family, or omitted
  relative to a sibling**, where the *first failing gate selects the player-facing
  message* (SHOUT-005, TELL-009, GIVE-003, RECITE-006, FIGHT-067 shape) — in the
  `fight.c` offensive-skill **entry gates**.
- **Last completed**:
  - **FIGHT-069** — `do_dirt` (`src/fight.c:2537-2542`) and `do_trip`
    (`:2678-2683`) both reject a kill-steal in ROM
    (`IS_NPC(victim) && victim->fighting && !is_same_group(ch, victim->fighting)`
    → "Kill stealing is not permitted."), but Python only called
    `_kill_safety_message` — `do_kill`'s **is_safe composite**, which bundles the
    is_safe messages + charm gate but **not** kill-steal (`do_kill` re-adds it
    separately at `combat.py:141`). `do_dirt` / `do_trip` inherited the omission,
    letting a player steal a kill by dirt-kicking / tripping a mob a third party
    was already fighting. Added the kill-steal block to both, at ROM's gate
    position. (v2.14.101)
  - Filed **FIGHT-071** (`do_dirt` / `do_trip` charm-friend message + gate order
    still diverge — the shared helper emits do_kill's "beloved master" line where
    ROM wants per-command charm strings at different positions).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT069_DIRT_TRIP_KILL_STEAL.md](SESSION_SUMMARY_2026-06-14_FIGHT069_DIRT_TRIP_KILL_STEAL.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.101 |
| Tests | 5791 passed / 4 skipped |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | fight.c offensive-skill entry-gate sweep (FIGHT-067 + FIGHT-069 closed); cross-file / divergence-class pass continues |

## Next Intended Task

Continue the fight.c offensive-skill entry-gate sweep: **FIGHT-071** (reconcile
the `do_dirt` / `do_trip` charm-friend message + gate order against ROM — the
shared `_kill_safety_message` helper emits `do_kill`'s "beloved master" line where
ROM wants per-command charm strings, `"$N is such a good friend!"` /
`"$N is your beloved master."`, at different positions) and **FIGHT-070** (extract
a shared message-emitting `is_safe` so the entry gates surface ROM's context lines
instead of silently swallowing them). **FIGHT-068** (do_bash `victim==ch` /
position order swap, MINOR) also open. All rows in `docs/parity/FIGHT_C_AUDIT.md`.
Beyond this verb family, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the
higher-yield open lever remains the **Hypothesis state-machine → diff_harness
widening** (Class 11 / Phase C), enumeration-independent (guardrail 3), where most
recent FINDING-0xx originated.
