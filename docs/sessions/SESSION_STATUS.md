# Session Status — 2026-05-25 → 26 — INV-016 → do_group notify (2.9.10 → 2.9.20)

## Current State

- **Active pass**: cross-file invariants + opportunistic gap closures.
  Eleven clusters landed this session: INV-016 (2.9.10), HPCNT-001
  (2.9.11), die_follower (2.9.12), INV-017 (2.9.13), INV-018 (2.9.14),
  group XP NPC level-1 floor (2.9.15), INV-019 (2.9.16),
  do_say/do_tell SPEECH gate (2.9.17), do_buy TO_ROOM (2.9.18),
  do_follow add/stop notify (2.9.19), do_group add/remove notify (2.9.20).
- **2.9.20** — `do_group` was returning only the TO_CHAR string.
  ROM `src/act_comm.c:1841-1846, 1850-1854` emits three messages on
  each path (TO_VICT, TO_NOTVICT, TO_CHAR). Victims never learned
  they had been added/removed; onlookers never saw membership
  changes. Same architectural pattern as 2.9.19 do_follow gap.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.20 |
| Tests | 4733 passed, 4 skipped (full suite, 9m02s) |
| Cross-file invariants | 19 of ~20 budget; INV-001 … INV-019 ✅ ENFORCED |
| Branch | `master` (2.9.10–2.9.19 on origin; 2.9.20 staged) |
| Watch list | do_group probe ✅ (gap closed, not INV) |

## Next Intended Task

The 2.9.19 + 2.9.20 cluster both close TO_VICT/TO_NOTVICT broadcast
gaps in `mud/commands/group_commands.py`. The duplicate
`add_follower`/`stop_follower`/`is_same_group` between
`mud/characters/follow.py` and `mud/commands/group_commands.py` is
now an active hazard — these will drift. Best next session: a
consolidation that removes the group_commands duplicates and routes
`do_follow` through `mud/characters/follow.py`.

Candidate areas for next probe (19/~20 INV budget):

1. **Duplicate-follow-impl consolidation** — merge group_commands
   `add_follower`/`stop_follower`/`is_same_group` into the
   `mud/characters/` canonical module; route `do_follow` and
   `do_group` through it. Multi-test, multi-file — likely its own
   session or small audit.
2. **INV-budget restructuring discussion** — at 19/~20, AGENTS.md
   notes reviewing the invariant taxonomy. Skim the per-file audit
   tracker for rows that should be lifted to INV.
3. **`do_value` price reporting voice gates** — ROM
   `src/act_obj.c:2965+` — probe TO_VICT vs TO_CHAR correctness.
4. **Group-membership-on-follow** — ROM `do_follow` does NOT auto-
   group; `is_same_group` only follows `leader`, not `master`. Probe
   `mud/groups/xp.py` and AoE targeting to verify they distinguish
   followers (master chain) from group (leader chain) per ROM.

Probe method: read ROM C contract → read Python equivalent → write
one failing test. Then close as single gap-closer or file INV-020.

No push to origin without explicit per-cluster user approval.
Pending push: 2.9.20.
