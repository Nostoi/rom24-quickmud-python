# Session Status — 2026-06-12 — FIGHT-060 check_assist elif chain (2.14.7)

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-060 — `check_assist` NPC elif chain misses ASSIST_ALIGN/ASSIST_VNUM
  when ASSIST_RACE flag set but race doesn't match. Python used `elif` for the five NPC OR-chain
  conditions; converted to independent `if` checks to match ROM `src/fight.c:139-150`.
  Two other probe candidates (violence_update room-mismatch, gain_exp level-cap) verified CLEAN.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_FIGHT060_CHECK_ASSIST_ELIF_CHAIN.md](SESSION_SUMMARY_2026-06-12_FIGHT060_CHECK_ASSIST_ELIF_CHAIN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.7 |
| Tests | 5611/5611 passing, 4 skipped (2026-06-12) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-045) |

## Next Intended Task

**Cross-file invariant probes** — three fresh candidates, probe-then-scope method:

1. **`check_assist` ASSIST_PLAYERS level check** — ROM `src/fight.c:116-124` ASSIST_PLAYERS
   path checks `rch->level + 6 > victim->level`. Verify Python uses the same operand order
   and comparison direction. Low-risk single-line check.
2. **`update_pos` missing position branches** — ROM `src/fight.c:1404-1435` `update_pos`
   handles RESTING/MEDITATING/SLEEPING → FIGHTING auto-stand transitions in addition to HP
   thresholds. Verify Python `mud/combat/engine.py:apply_position_change` covers all cases.
3. **`group_gain` party-size scaling** — ROM `src/fight.c:1736-1788` walks `in_room->people`
   for group members and applies the `group_levels` divisor. Verify Python
   `mud/groups/xp.py:group_gain` uses `room.people` and the correct level-sum formula.

For each: read ROM C contract → read Python equivalent → write one failing test if divergence
found → close as single-gap commit or file as INV-NNN.
