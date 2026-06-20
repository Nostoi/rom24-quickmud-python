# Session Status — 2026-06-19 — ARITH-210 + WIZ-053 (position-transition probe)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  remains exhausted). This loop session closed the last documented ARITH gap
  (**ARITH-210**) and one probe-surfaced position-transition divergence
  (**WIZ-053**). 9 probes across 8 subsystems otherwise confirmed parity — the
  documented-gap surface is genuinely drained. Stopped at the honest number of
  real gaps (2) rather than padding to the loop's target of 5.
- **Last completed** (master, committed — push pending until verified):
  - v2.14.174 — **ARITH-210**: mob spawn `current_hp = max_hit` raw (drop the
    `max_hit == 0` zero floor; ROM `src/db.c:2077`). Drains ARITHMETIC_BOUNDARY.
  - v2.14.175 — **WIZ-053**: `do_restore` re-evaluates position via `update_pos`
    instead of `position < STANDING` (ROM `src/act_wiz.c:2808/2840/2861`), so
    resting/sitting/sleeping victims are no longer wrongly stood up.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_ARITH-210_WIZ-053_POSITION_PROBE.md](SESSION_SUMMARY_2026-06-19_ARITH-210_WIZ-053_POSITION_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.175 |
| Tests | 5899 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep |
| Open findings | ARITHMETIC_BOUNDARY drained (0 open); ACT_WIZ_C no open gaps |

## Next Intended Task

The documented per-file + ARITH gap surface and the obvious combat/position/affect
probe candidates are exhausted. Two paths for the next session:

1. **Scope FINDING-001 with the user** — the single highest-impact remaining
   parity bug. The `.are`→JSON converter field-shifts mob HP/mana/damage dice, so
   **62/65 midgaard mobs (likely all JSON-loaded mobs game-wide)** have wrong HP.
   Fix = regenerate every `data/areas/*.json` + add a regression. Wide blast
   radius — needs user scoping, not an unattended loop. See
   `tools/diff_harness/FINDINGS.md`.
2. **Probe less-traveled subsystems** not covered this session — OLC save
   round-trips, shop/healer economics, weather/time, reset edge cases,
   mob-program triggers. Use `/rom-divergence-sweep` for the completeness lens.

**Doc-hygiene debt:** `docs/parity/BOARD_C_AUDIT.md` function-table rows (~30–48)
carry stale ❌/⚠️ statuses for gaps the gap-table records as ✅ FIXED — reconcile.

**Infra note:** GitNexus MCP server dropped its connection mid-session (impact/
detect_changes unavailable); fell back to grep for blast radius. The on-disk graph
was reindexed clean (only the known `src/recycle.h`/`olc.h` C-header scope warnings).
Confirm the MCP reconnects next session before relying on `gitnexus_*`.
