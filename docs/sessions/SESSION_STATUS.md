# Session Status — 2026-06-12 — xdist flakes fixed; cross-file invariants is the active pass

## Current State

- **Active focus**: Cross-file invariants pass (per-file audit tracker exhausted —
  only deferred track-only DB2 rows remain)
- **Last completed**: Both known xdist flakes fixed (test-isolation hardening, no
  production change) — `test_hpcnt_fires_exactly_once_per_violence_tick` (registry
  isolation) and `test_ac_clamping_for_negative_values` (pin `number_bits` not
  `number_percent`) (v2.14.23, commit `25e195ef`)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md](SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.23 |
| Tests | combat parity 10/10, hpcnt 2/2; full suite last green 5655 passed / 4 skipped (v2.14.21) |
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
