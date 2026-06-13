# Session Status — 2026-06-13 — INV-049 (spec_fun dispatched inside mobile_update, gated + suppressing) + GL-044 (mobile_update wander RNG primitive) + INV-048 (assist-is-violence-update-only); cross-file invariants is the active pass

## Current State

- **Active focus**: Cross-file invariants pass (per-file audit tracker exhausted —
  only deferred track-only DB2 rows remain)
- **Last completed**: INV-049 — mob special procedures are now dispatched INSIDE
  the `mobile_update` per-mob loop (`mud/ai/__init__.py`) at the ROM position
  (`src/update.c:425-431`): after the charm/empty-area gates, before shop-gold,
  triggers, scavenge, and wander, with a TRUE result `continue`ing to skip the
  rest of that mob's tick. The previous code ran `run_npc_specs()` as a separate
  pass over `room_registry` after the whole loop, bypassing the charm/empty gates
  and the TRUE-suppression and reordering the shared MM RNG draws.
  `run_npc_specs()` is kept as a test/manual entry point only and removed from
  `game_tick` (v2.14.31). Before that: GL-044 — `mobile_update` wander now draws its direction
  with `number_bits(5)` (single 5-bit roll, aborts when >5 → wanders 6/32 of
  eligible ticks), mirroring ROM `src/update.c:498`. Previously used
  `number_door()` (the do_flee primitive, `src/db.c:3541`) which re-rolls until
  ≤5 and never aborts — mobs wandered ~5× too often and the variable reroll loop
  desynced the shared Mitchell-Moore stream (v2.14.30). Before that: INV-048 —
  auto-assist (`check_assist`) now fires from
  exactly one site, `game_loop.violence_tick` (ROM `src/fight.c:90`,
  `violence_update`). Removed the erroneous inline `check_assist` from
  `mud/ai/aggressive.py:aggressive_update` — ROM `aggr_update` (`src/update.c:1136`)
  ends each aggression with a bare `multi_hit` and never assists, so assists land
  on the next violence tick, not the aggression pulse. The stray call started
  assists a tick early and drew extra coins from the shared MM RNG stream
  (v2.14.29). Earlier this session: INV-020 step (v) carried+worn object extract
  on every non-death extract leg (v2.14.28, `34519468`), INV-020 step (iv)
  `stop_fighting(both=True)` on quit+disconnect (v2.14.27, `20c22cb1`), INV-047
  multi-path extract-ref cleanup (v2.14.26, `cb67db83`), INV-047 single-path
  mprog_target quirk (v2.14.25), MOBCMD-019 (v2.14.24), xdist flakes (v2.14.23)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md](SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.31 |
| Tests | mob-AI 21/21, full suite last green 5676 passed / 4 skipped (v2.14.31) |
| INV-049 status | ✅ ENFORCED (spec_fun dispatched inside mobile_update — gated by charm/empty, TRUE-result suppresses rest of tick; no separate run_npc_specs pass) |
| GL-044 status | ✅ FIXED (mobile_update wander uses number_bits(5), aborts >5; not number_door) |
| INV-048 status | ✅ ENFORCED (check_assist fires only from violence_tick; aggr_update never assists) |
| INV-020 status | ✅ ENFORCED (full extract_char chain — steps i–v — on all extract legs: raw_kill, _extract_character, quit, disconnect) |
| INV-047 status | ✅ ENFORCED (extract-ref cleanup on all paths) |
| INV-046 status | ✅ ENFORCED (phantom-registry class fully closed + grep-guarded) |
| Per-file OPEN gaps | 0 live (DB2-004/005 deferred track-only) |
| Active focus | Cross-file invariants probe |

## Next Intended Task

The per-file audit tracker has no live `🔄 OPEN` rows; cross-file invariants is the
primary pass. Use the probe-then-scope method (read ROM C contract → read Python
equivalent → one failing test → close as a single gap or file as the next free
INV-NNN). Candidates:

1. **Mob memory / hunt** — `src/fight.c` ATTACK_BACK and the hunt/track loop vs the
   Python AI tick (not yet probed).
2. **Position-transition edges** — `update_pos` / `stop_fighting` ordering across
   damage, sleep, rest, and death.

Confirmed-faithful (do not re-probe without new evidence): weather/time fan-out and
`update_handler` pulse cadence (locked by `tests/test_game_loop_order.py` +
`tests/integration/test_weather_time.py`); `stop_fighting` position semantics and
mob prototype-count recompute (recall-oracle confirmed this session).

**Process reminder:** after every phantom-class / list-walk fix, re-grep the whole
`mud/` tree before trusting a hand-built site inventory — family 3a's inventory
missed 2 sites that the family-3b re-grep caught.
