# Session Status — 2026-06-19 — HEALER-005/006 (divergence-sweep probe)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  remains exhausted). This loop session ran probe-then-scope and closed **2 real
  gaps in `healer.c`** — a file previously marked ✅ AUDITED — plus reconciled 2
  stale "deferred to P2" doc rows. Weather/time and drink probes confirmed parity.
  Stopped at the honest number of real gaps (2) rather than padding to the loop's
  ceiling of 10 (advisor-endorsed; matches the prior loop session).
- **Last completed** (master, committed — push pending until verified):
  - v2.14.176 — **HEALER-005**: insufficient-funds refusal now uses ROM's
    `act("$N says '...'")` wrapper (`src/healer.c:171-176`), capitalized via
    `capitalize_act_line`. Was a bare line, inconsistent with sibling branches.
  - v2.14.177 — **HEALER-006**: healer service match order now follows ROM's
    if/else (`mana` before `refresh`, `src/healer.c:147/156`) via a new
    `_MATCH_ORDER`, decoupled from the price-list display order. `heal m` now
    resolves to mana (1000 silver) not refresh (500), matching ROM.
  - Doc-hygiene: reconciled stale position-furniture and pet-persistence P2 rows
    (both already implemented; the "deferred to P2" labels AGENTS.md forbids).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_HEALER_005_006_DIVERGENCE_PROBE.md](SESSION_SUMMARY_2026-06-19_HEALER_005_006_DIVERGENCE_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.177 |
| Tests | 5901 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep |
| Open findings | `healer.c` re-closed at 6/6 gaps; documented surface drained |

## Next Intended Task

Documented per-file + ARITH gap surface stays drained; cross-file /
divergence-sweep is the primary pass. This session's probe-then-scope found 2
real gaps in `healer.c`; the other surfaces probed (weather/time, drink) are
faithful. Three paths for the next session:

1. **Continue probe-then-scope on less-traveled subsystems not yet covered** —
   OLC save round-trips, shop `do_buy` haggle/credit edges, reset edge cases,
   mob-program trigger dispatch, bank/deposit, `do_practice`/`do_gain`. Use
   `/rom-divergence-sweep` for the completeness lens. Healer/weather/drink are now
   exhausted — pick a fresh surface.
2. **FINDING-001** (`tools/diff_harness/FINDINGS.md`) — highest-impact remaining
   bug: the `.are`→JSON converter field-shifts mob HP for 62/65 midgaard mobs.
   WIDE blast radius (regenerate every `data/areas/*.json`) — **scope with the
   user**, not an unattended loop.
3. **Doc-hygiene:** `docs/parity/BOARD_C_AUDIT.md` function-table rows (~30-48)
   still carry stale ❌/⚠️ for gaps the gap-table records as ✅ FIXED — reconcile.

**Infra note:** GitNexus MCP reconnected this session; `detect_changes` returned
LOW risk on both healer commits (scope confined to `do_heal` + audit doc). The
on-disk graph was reindexed cleanly twice (only the known `src/recycle.h`/`olc.h`
C-header scope warnings). Index will show stale at session end (the handoff doc
commit lands post-reindex) — next session's first action reindexes per
STOP-AND-REINDEX. Three surfaces (README/SESSION_STATUS/pyproject) reconcile at
2.14.177 once committed.
