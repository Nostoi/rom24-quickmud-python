# Session Status — 2026-06-13 — extract_char cleanup chain complete on all paths (INV-047 + INV-020 step iv); cross-file invariants is the active pass

## Current State

- **Active focus**: Cross-file invariants pass (per-file audit tracker exhausted —
  only deferred track-only DB2 rows remain)
- **Last completed**: INV-020 step (iv) — the quit + disconnect extract legs now
  call `stop_fighting(char, both=True)` (`src/handler.c:2121`), completing ROM's
  4-step `extract_char` cleanup chain on all four Python extract legs (v2.14.27,
  commit `20c22cb1`). Earlier this session: INV-047 multi-path extract-ref
  cleanup across all extract paths (v2.14.26, `cb67db83`), INV-047 single-path
  mprog_target quirk (v2.14.25, `0f7cd666`), MOBCMD-019 `do_mpremember`
  stale-target clear (v2.14.24, `6725c202`), and both known xdist flakes fixed
  (v2.14.23, `25e195ef`)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md](SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.27 |
| Tests | extract/fighting regression 56/56; full suite last green 5655 passed / 4 skipped (v2.14.21) |
| INV-020 status | ✅ ENFORCED (full 4-step extract_char chain on all four legs: raw_kill, _extract_character, quit, disconnect) |
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
