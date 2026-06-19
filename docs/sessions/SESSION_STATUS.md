# Session Status — 2026-06-19 — ARITH-208 dice+divisor coupling (CLOSED)

## Current State

- **Active focus**: Cross-file / divergence-class sweep. The per-file audit
  tracker remains exhausted. This session closed **ARITH-208** — the last
  entangled reset/spawn arithmetic item — as a coordinated source + divisor
  change (probe → TDD → implement → differential gate → full suite). The
  reset/spawn divergence surface (DB-003 + ARITH-208) is now **fully drained**.
- **Last completed** (master, **committed — push pending until verified**):
  - v2.14.173 — **ARITH-208**: mob hp/mana spawn roll no longer floored at 0
    (`templates._roll_dice` returns raw `dice()+bonus`, ROM `src/db.c:2074-2077`);
    coupled UB-divisor floors narrowed from `max(1, x)` to a zero-only guard
    (`x or 1`) + `c_div` at do_berserk, dam_message, mobprog hpcnt/HPCT, and the
    `engine.py` `max_hit/4` injury thresholds, so a negative `max_hit` flows
    through both sides (ROM `neg/neg = positive`). The mobprog sites also moved
    bare `//` → `c_div` (latent floor-vs-truncation fix). 5 new tests.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_ARITH-208_DICE_DIVISOR_COUPLING.md](SESSION_SUMMARY_2026-06-19_ARITH-208_DICE_DIVISOR_COUPLING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.173 |
| Tests | 5895 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep |
| Open findings | **ARITH-114** (get_curr_stat ceiling), **ARITH-210** (templates `current_hp` zero floor) |

## Next Intended Task

The reset/spawn divergence surface is fully drained. The ARITH backlog is down to
two ❌: **ARITH-114** (`get_curr_stat` per-race/class ceiling) and **ARITH-210**
(`templates.py` `current_hp` floors the `max_hit == 0` spawn case to ≥ 1 where ROM
sets `hit = max_hit = 0`; surfaced this session, needs a reachability probe before
the floor is removed — see `docs/parity/audits/ARITHMETIC_BOUNDARY.md`).

Cross-file / divergence-class sweep is the primary pass. Candidate areas with no
INV row yet: **affect ticks**, **position transitions**, **mob script triggers**,
**group/follower chain**. Use the probe-then-scope method (read ROM C contract →
read Python equivalent → one failing contract test → close as a single gap commit
or file as the next free INV-NNN). Feature-sized alternatives: BOARD-001 (default
board seeding), OLC save paths. Run `/rom-divergence-sweep` for the completeness
lens (which verification layer each divergence class needs).

**Infra note:** GitNexus MCP query tools were live this session
(`detect_changes` confirmed low risk, scope confined to the 6 expected symbols +
docs). A PostToolUse stale-index reindex may fire after the ARITH-208 commit;
confirm it completes clean before relying on `gitnexus_*` again next session.
