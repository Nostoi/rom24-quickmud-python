# Session Status — 2026-06-12 — FIGHT-061 do_flee move cost (2.14.8)

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-061 — `do_flee` movement deduction had three divergences from ROM:
  wrong formula (`max_move/10` instead of sector-average), no IS_NPC guard (NPCs had move
  deducted), and no exhaustion check (PC with insufficient move could still flee). Fixed by
  integrating sector-based cost computation with PC guard and exhaustion `continue` inside the
  6-attempt loop. ROM reference: `src/fight.c:3001-3002`, `src/act_move.c:115-193`.
  Five probe candidates verified this session: ASSIST_PLAYERS level check, update_pos,
  group_gain, tick_spell_effects — all CLEAN; do_flee move cost — FIGHT-061 filed and closed.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_FIGHT061_DO_FLEE_MOVE_COST.md](SESSION_SUMMARY_2026-06-12_FIGHT061_DO_FLEE_MOVE_COST.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.8 |
| Tests | 5614/5614 passing, 4 skipped (2026-06-12) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-045) |

## Next Intended Task

**Cross-file invariant probes** — three fresh candidates, probe-then-scope method:

1. **`do_recall` movement cost** — ROM `src/act_move.c:do_recall` also calls `move_char` for
   movement. Verify Python's `do_recall` uses the correct sector-based deduction (not a flat
   formula like the now-fixed `do_flee`). Low-risk, sibling of FIGHT-061.
2. **`violence_update` mid-tick death** — ROM `src/fight.c:63-103` sets `rch_next` before the
   loop body and handles character death mid-tick safely. Verify Python `violence_tick` in
   `mud/game_loop.py` doesn't iterate over a live list that `raw_kill` can mutate.
3. **`do_rescue` stop-fighting / multi-hit ordering** — ROM `src/fight.c:3032-3107` re-routes
   the attacker with `stop_fighting(victim, FALSE)` then `multi_hit(victim, ch, ...)`. Verify
   Python `do_rescue` mirrors this order and doesn't double-call `stop_fighting`.

For each: read ROM C contract → read Python equivalent → write one failing test if divergence
found → close as single-gap commit or file as INV-NNN.
