# Session Status — 2026-06-14 — fight.c dirt/trip charm gate (FIGHT-071)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). Following the "category-error / borrowed-gate" lead — a precondition
  checked in the wrong order, **borrowed from the wrong command family, or omitted
  relative to a sibling**, where the *first failing gate selects the player-facing
  message* (SHOUT-005, TELL-009, GIVE-003, RECITE-006, FIGHT-067, FIGHT-069 shape)
  — in the `fight.c` offensive-skill **entry gates**.
- **Last completed**:
  - **FIGHT-071** — `do_dirt` (`src/fight.c:2544-2548`) and `do_trip`
    (`:2705-2709`) charm gate. Both routed their charmed-attacker-vs-master check
    through `_kill_safety_message` (do_kill's is_safe composite), which emitted
    do_kill's `"$N is your beloved master."` at the **top** of the helper. ROM
    checks charm **last** with per-command strings: do_dirt `"But $N is such a
    good friend!"`, do_trip `"$N is your beloved master."` only after the
    flying/position/self checks. Added `include_charm: bool = True` to the helper
    (do_kill keeps default → byte-identical); do_dirt/do_trip now pass
    `include_charm=False` and carry their own correctly-worded, correctly-ordered
    charm gate (FIGHT-067 `do_bash` pattern). (v2.14.102)
  - Filed out-of-scope **FIGHT-072** (do_dirt victim==ch before AFF_BLIND order
    swap), **FIGHT-073** (do_dirt BLIND message literal "They're" vs ROM `$E`),
    **FIGHT-074** (do_kill charm checked before is_safe body + kill-steal).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT071_DIRT_TRIP_CHARM_GATE.md](SESSION_SUMMARY_2026-06-14_FIGHT071_DIRT_TRIP_CHARM_GATE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.102 |
| Tests | 5794 passed / 4 skipped (full suite last run at 2.14.101 = 5791; +3 FIGHT-071) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | fight.c offensive-skill entry-gate sweep (FIGHT-067 + FIGHT-069 + FIGHT-071 closed); cross-file / divergence-class pass continues |

## Next Intended Task

Continue the fight.c offensive-skill entry-gate sweep. Open rows in
`docs/parity/FIGHT_C_AUDIT.md`:

- **FIGHT-074** — bring `do_kill` onto the same charm-last ordering (move the
  charm check in `_kill_safety_message` after the is_safe body; have `do_kill`
  apply charm after its kill-steal gate). Completes the kill/dirt/trip charm-order
  trio that FIGHT-071 started.
- **FIGHT-070** — extract a shared message-emitting `is_safe` so the entry gates
  surface ROM's context lines ("Not in this room.", shopkeeper, pet, …) instead
  of silently swallowing them. Structural; affects every bool-`is_safe` entry gate.
- **FIGHT-072 / FIGHT-073** — do_dirt BLIND order swap + `$E` pronoun message
  (MINOR, act()-render class). **FIGHT-068** — analogous do_bash `victim==ch`/
  position order swap.

Beyond this verb family, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the
higher-yield open lever remains the **Hypothesis state-machine → diff_harness
widening** (Class 11 / Phase C), enumeration-independent (guardrail 3), where most
recent FINDING-0xx originated.
