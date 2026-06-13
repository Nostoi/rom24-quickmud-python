# Session Status — 2026-06-13 — extract_char cleanup chain complete on all paths (INV-020 steps i–v + INV-047); cross-file invariants is the active pass

## Current State

- **Active focus**: Cross-file invariants pass (per-file audit tracker exhausted —
  only deferred track-only DB2 rows remain)
- **Last completed**: INV-020 step (v) — every non-death extract leg now extracts
  the character's carried AND worn objects via the shared
  `mud/combat/death.py:extract_carried_objects` helper (ROM `src/handler.c:2123-2127`
  walks `ch->carrying`, which includes worn items). Wired into the link-dead quit
  leg, the socket-disconnect teardown, and the mob/`do_purge` leg
  (`_extract_character`, previously inventory-only → leaked equipped objects into
  `object_registry`). Closes a phantom-object leak (INV-046 class) on the extract
  path (v2.14.28). Earlier this session: INV-020 step (iv) `stop_fighting(both=True)`
  on quit+disconnect (v2.14.27, `20c22cb1`), INV-047 multi-path extract-ref cleanup
  (v2.14.26, `cb67db83`), INV-047 single-path mprog_target quirk (v2.14.25,
  `0f7cd666`), MOBCMD-019 (v2.14.24, `6725c202`), xdist flakes (v2.14.23,
  `25e195ef`)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md](SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.28 |
| Tests | extract/fighting/purge regression 16/16; full suite last green 5671 passed / 4 skipped (v2.14.27) |
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
