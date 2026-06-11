# Session Status — 2026-06-11 — FIGHT-054 do_flee mechanism closed

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-054 (`mud/commands/combat.py:do_flee` — replaced fake dex-chance
  `number_percent()` roll with ROM's 6-attempt `number_door()` loop; added EX_CLOSED (bit 1),
  daze check `number_range(0, ch->daze)`, NPC `ROOM_NO_MOB` guard, and `POS_STANDING` reset
  to match ROM `src/fight.c:2970-3003`)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-11_FIGHT054_DO_FLEE_MECHANISM.md](SESSION_SUMMARY_2026-06-11_FIGHT054_DO_FLEE_MECHANISM.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.0 |
| Tests | 2927/2930 passing, 3 skipped (full suite run 2026-06-11) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

INV-044 slot is free. Three previous STATUS probes are now closed (group-leader death — no gap;
affect_update expiry dedup — no gap; do_flee — FIGHT-054 closed). Suggested next probes:

1. **`do_rescue` stop-fighting argument** — ROM `src/fight.c:3094-3095` calls
   `stop_fighting(ch, FALSE)` and `stop_fighting(victim, FALSE)` (the `FALSE` means the
   victim's opponents are NOT also stopped, unlike `do_flee`'s `TRUE`). Python `do_rescue`
   (`mud/commands/combat.py`) — verify both calls use the correct `FALSE` argument.

2. **`violence_update` position guard** — ROM `src/fight.c:2645-2651` skips characters
   where `position != POS_FIGHTING` AND `position != POS_RESTING`. Verify Python
   `violence_tick` (mud/game_loop.py) has an equivalent guard so sleeping/stunned characters
   don't participate in combat rounds.

3. **`check_assist` ASSIST_ALL vs group-assist ordering** — ROM uses a single
   `if (flag || group || ...)` expression; Python uses `if/elif` then a separate
   `if ch_group...` block. Verify no behavioral difference when BOTH a flag AND group match.
