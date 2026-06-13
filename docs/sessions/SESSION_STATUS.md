# Session Status — 2026-06-12 — WIZ-051 closed; cross-file invariants is the active pass

## Current State

- **Active focus**: Cross-file invariants pass (per-file audit tracker exhausted — only deferred
  track-only DB2 rows remain)
- **Last completed**: WIZ-051 — `find_location` object fallback (`at`/`goto`/`transfer <obj>` now
  resolves to the room an object lies in) (v2.14.22, commit `a99718f9`)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_WIZ051_AND_CROSS_INV_PROBE.md](SESSION_SUMMARY_2026-06-12_WIZ051_AND_CROSS_INV_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.22 |
| Tests | act_wiz parity suite 121/121; full suite last green at 5655 passed / 4 skipped (v2.14.21) |
| INV-046 status | ✅ ENFORCED (phantom-registry class fully closed + grep-guarded) |
| Per-file OPEN gaps | 0 live (DB2-004/005 deferred track-only) |
| Active focus | Cross-file invariants probe |

## Next Intended Task

The per-file audit tracker has no live `🔄 OPEN` rows; cross-file invariants is the primary pass.
Use the probe-then-scope method (read ROM C contract → read Python equivalent → one failing test →
close as a single gap or file as the next free INV-NNN). Candidates:

1. **Mob memory / hunt** — `src/fight.c` ATTACK_BACK and the hunt/track loop vs the Python AI tick.
2. **`weather_update` message fan-out order** — ROM broadcast ordering across the descriptor walk.
3. **`update_handler` pulse cadence** — ROM pulse counters (PULSE_VIOLENCE, PULSE_MOBILE, …) vs the
   Python tick scheduler.
4. **Diagnose the two xdist flakes** — `test_ac_clamping_for_negative_values`,
   `test_hpcnt_fires_exactly_once_per_violence_tick`; isolate with `-n0`, reproduce with `-n auto`.

**Process reminder:** after every phantom-class / list-walk fix, re-grep the whole `mud/` tree
before trusting a hand-built site inventory — family 3a's inventory missed 2 sites that the
family-3b re-grep caught.
