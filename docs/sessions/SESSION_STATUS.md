# Session Status — 2026-06-10 — FIGHT-053 check_assist RNG increment closed

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-053 (`mud/combat/assist.py:check_assist` — target-selection
  loop `number++` moved inside selection block to match ROM `src/fight.c:165` and keep
  MM RNG stream in sync)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-10_FIGHT053_CHECK_ASSIST_RNG_INCREMENT.md](SESSION_SUMMARY_2026-06-10_FIGHT053_CHECK_ASSIST_RNG_INCREMENT.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.99 |
| Tests | 42/42 FIGHT-04x/05x passing (prior full run: 2903 passed, 3 skipped + 12 new tests this day) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

INV-044 slot is free. Suggested next probes:

1. **Group-leader death handoff** — ROM `raw_kill` → follower cleanup. When a group leader
   dies, ROM `stop_follower` clears all follower leader-pointers. Verify Python's
   `_extract_character` / `_nuke_pets` path handles group leadership transfer correctly.
   If `is_same_group` can return True for a dead leader's former followers vs each other,
   that's a cross-file bug worth filing as INV-044.

2. **`affect_update` expiry dedup check** — ROM `src/update.c:774-775` skips the `msg_off`
   message when `paf_next->type == paf->type && paf_next->duration > 0` (two stacked affects
   of same spell, only send message on the last one). Verify `tick_spell_effects`
   (`mud/affects/engine.py`) replicates this exactly with the `should_emit` guard.

3. **`do_flee` position after flee** — ROM `move_char` sets `ch->position = POS_STANDING`
   before `stop_fighting` is called. Python `do_flee` calls `stop_fighting` which also sets
   position. Verify no position state is leaked if flee fails mid-movement.
