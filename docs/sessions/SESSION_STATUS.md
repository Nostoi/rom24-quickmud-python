# Session Status — 2026-06-14 — fight.c bash entry-gate (FIGHT-067)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). Following the "category-error / borrowed-gate" lead — a precondition
  checked in the wrong order, **borrowed from the wrong command family, or omitted
  relative to a sibling**, where the *first failing gate selects the player-facing
  message* (SHOUT-005, TELL-009, GIVE-003, RECITE-006 shape) — now into the
  `fight.c` offensive-skill **entry gates**.
- **Last completed**:
  - **FIGHT-067** — `do_bash` was missing ROM's entry-level offensive-target gate
    block (`is_safe` / kill-steal / charm-friend, `src/fight.c:2405-2419`), checked
    *before* chance/WAIT_STATE/daze/knockdown. Python relied solely on
    `apply_damage`'s silent downstream `is_safe` re-check (FIGHT-002), which
    suppresses only HP damage — so in a ROOM_SAFE room a bash still lagged the
    attacker, dazed the victim, knocked them to RESTING, and broadcast "sends you
    sprawling" (a real safe-room griefing divergence). Added the ROM gate block:
    `is_safe` → silent short-circuit; kill-steal → "Kill stealing is not
    permitted."; charm-friend → `act_format("But $N is your friend!", …)`.
    (v2.14.100)
  - Filed three follow-ups in `docs/parity/FIGHT_C_AUDIT.md`: **FIGHT-068**
    (entry-gate order swap `victim==ch` vs position), **FIGHT-069** (do_trip/do_dirt
    entry-gate parity, likely same shape), **FIGHT-070** (is_safe context-message
    surfacing — bool `is_safe` swallows ROM's "Not in this room." etc.).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT067_BASH_ENTRY_GATE.md](SESSION_SUMMARY_2026-06-14_FIGHT067_BASH_ENTRY_GATE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.100 |
| Tests | 5789 passed / 4 skipped |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | fight.c offensive-skill entry-gate sweep (FIGHT-067 closed); cross-file / divergence-class pass continues |

## Next Intended Task

Continue the fight.c offensive-skill entry-gate sweep: **FIGHT-069** (apply the
identical `is_safe` / kill-steal / charm entry-gate diff to `do_trip` / `do_dirt`,
which almost certainly share FIGHT-067's omission) and **FIGHT-070** (extract a
shared message-emitting `is_safe` so the entry gates surface ROM's context lines
instead of silently swallowing them). Both rows are in
`docs/parity/FIGHT_C_AUDIT.md`. Beyond this verb family, per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open lever remains the
**Hypothesis state-machine → diff_harness widening** (Class 11 / Phase C),
enumeration-independent (guardrail 3), where most recent FINDING-0xx originated.
