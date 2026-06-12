# Session Status — 2026-06-11 — INV-044 charm-master attacks own pet (2.14.5)

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: INV-044 — added `stop_follower(victim)` inside `apply_damage`
  when `victim.master is attacker`, mirroring ROM `src/fight.c:756-757`. Three
  other INV-044 probe candidates (kill/XP/trigger ordering, iterator safety,
  position-transitions under multi-attack) were verified CLEAN.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-11_INV044_CHARM_MASTER_ATTACKS_PET.md](SESSION_SUMMARY_2026-06-11_INV044_CHARM_MASTER_ATTACKS_PET.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.5 |
| Tests | 5608/5608 passing, 4 skipped (2026-06-11) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-045) |

## Next Intended Task

**INV-045 cross-file probe** — three fresh candidate areas, probe-then-scope method:

1. **Position-transition broadcast** — when a victim is knocked from FIGHTING →
   STUNNED, does Python send the correct ROM act() room messages? Read ROM C
   `src/fight.c:update_pos` + `src/fight.c:damage` position-change block, read
   Python `mud/combat/engine.py:update_pos` + `apply_position_change`, write one
   failing test if broadcast diverges.
2. **`stop_fighting` both=False call sites** — ROM `src/fight.c:stop_fighting`
   with `fBoth=FALSE` only clears the victim's own `fighting` pointer (not the
   full char_list sweep). Verify Python `stop_fighting(ch, both=False)` matches
   and that every call site uses the right flag.
3. **`check_killer` cross-file coherence** — ROM `src/fight.c:check_killer` sets
   `PLR_KILLER` on the attacker; Python calls `_mark_killer_if_needed` from
   `apply_damage`. Verify the condition guards and cross-file contract are exact.

For each: read ROM C contract → read Python equivalent → write one failing test
if divergence exists → close as single-gap commit or file as INV-NNN.
