# Session Status — 2026-06-10 — FIGHT-052 kill safety guard ordering closed

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-052 (`mud/commands/combat.py:_kill_safety_message` — NPC-attacker
  safe-room / charmed-mob guard order swapped to match ROM `src/fight.c:1083-1087`)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-10_FIGHT052_KILL_SAFETY_GUARD_ORDER.md](SESSION_SUMMARY_2026-06-10_FIGHT052_KILL_SAFETY_GUARD_ORDER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.98 |
| Tests | 2903 passed, 3 skipped (prior full run) + 11 new tests this session (FIGHT-050: 6, FIGHT-051: 4, FIGHT-052: 1) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

INV-044 slot is free. Suggested next probe:

**`do_flee` / `do_recall` stop-fighting contract** — both call `stop_fighting(ch, True)` after
the action succeeds. Verify ROM C `do_flee` (`:3094-3095`: two separate `stop_fighting(fch, FALSE)`
calls, NOT `TRUE`) and `do_recall` (`:1699`: `stop_fighting(victim, TRUE)`) — the Python may be
using `both=True` where ROM uses `both=False` for flee. If the Python `do_flee` uses `True`
when ROM uses `FALSE`, it over-clears the opponent's fighting pointer, which could be a
divergence worth filing as FIGHT-053 or INV-044.
