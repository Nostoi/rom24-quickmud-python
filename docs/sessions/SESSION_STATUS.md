# Session Status — 2026-06-13 — INV-047 extract-cleanup closed on all paths; cross-file invariants is the active pass

## Current State

- **Active focus**: Cross-file invariants pass (per-file audit tracker exhausted —
  only deferred track-only DB2 rows remain)
- **Last completed**: INV-047 (multi-path) — the ROM `extract_char` dangling-ref
  cleanup (`reply` + `mprog_target` quirk, `src/handler.c:2151-2157`) extracted
  into a shared `clear_extract_target_refs` helper and wired into all three
  Python extract paths (`_extract_character`, `_auto_quit_character` quit leg,
  `_disconnect_extract_cleanup` socket leg) — same multi-path class INV-020
  closed for nuke_pets/die_follower (v2.14.26, commit `cb67db83`). Earlier this
  session: INV-047 single-path mprog_target quirk (v2.14.25, `0f7cd666`),
  MOBCMD-019 `do_mpremember` stale-target clear (v2.14.24, `6725c202`), and both
  known xdist flakes fixed (v2.14.23, `25e195ef`)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md](SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.26 |
| Tests | INV-047 multi-path 10/10, extract/death suites 38/38; full suite last green 5655 passed / 4 skipped (v2.14.21) |
| INV-047 status | ✅ ENFORCED (extract-cleanup on all paths: _extract_character + quit leg + disconnect leg) |
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
`tests/integration/test_weather_time.py`). The two prior xdist flakes are now
resolved — drop them from Outstanding.

**Process reminder:** after every phantom-class / list-walk fix, re-grep the whole
`mud/` tree before trusting a hand-built site inventory — family 3a's inventory
missed 2 sites that the family-3b re-grep caught.
