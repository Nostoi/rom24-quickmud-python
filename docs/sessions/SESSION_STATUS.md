# Session Status — 2026-05-27 — ARITH-107 + level-0 dice cluster (2.9.75/76)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) filed in
  2.9.64; cumulative close-out through 2.9.76 has now closed
  **15 FIXED** and **17 N/A** of the 46 triaged ARITH-NNN candidates
  (45 original + 1 follow-on ARITH-114). **14 ❌ MISSING remain**.
- **Last completed** (2 commits this session, 5 gap IDs):
  - **`ARITH-107`** — ✅ FIXED (2.9.75). `Room.remove_character`
    floor `max(0, current - 1)` removed at
    `mud/models/room.py:171`. Now matches ROM
    `src/handler.c:1502` bare `--area->nplayer`. Regression:
    `tests/integration/test_arith_107_nplayer_no_floor.py` (3/3).
  - **`ARITH-020` / `ARITH-021` / `ARITH-022` / `ARITH-023`** —
    ⛔ N/A (2.9.76). Level-0 spell/skill dice cluster
    reclassified as dead defensive code after ROM-source probe:
    - ARITH-020 (`spell_energy_drain` dice): unreachable via
      do_cast level/class gate.
    - ARITH-021/022 (fire/frost_breath `saves_spell(level-2)`):
      dispatched only via spec_breath_fire/frost spec_funs on
      high-level dragon mobs.
    - ARITH-023 (`do_kick` `number_range(1, level)`): unreachable
      via ch->fighting + skill-check gates; also a no-op even if
      reached (ROM `number_range(1, 0)` returns 1 via to<from
      branch). ROM-cite comments added at all four sites.
  - Full integration suite: **2340 passed, 3 skipped** in 84.95s.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_107_AND_LEVEL_ZERO_CLUSTER.md](SESSION_SUMMARY_2026-05-27_ARITH_107_AND_LEVEL_ZERO_CLUSTER.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_ARITH_CARRY_COUNTER_CLUSTER.md](SESSION_SUMMARY_2026-05-27_ARITH_CARRY_COUNTER_CLUSTER.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_105_AND_110.md](SESSION_SUMMARY_2026-05-27_ARITH_105_AND_110.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_005_AND_209.md](SESSION_SUMMARY_2026-05-27_ARITH_005_AND_209.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_001_002_003_RECLASS.md](SESSION_SUMMARY_2026-05-27_ARITH_001_002_003_RECLASS.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_UB_DIVISOR_CLOSEOUT.md](SESSION_SUMMARY_2026-05-27_ARITH_UB_DIVISOR_CLOSEOUT.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md](SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md](SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md](SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md](SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.76 |
| Tests | Full integration suite **2340 passed, 3 skipped** in 84.95s. ARITH-107 regression `test_arith_107_nplayer_no_floor.py` 3/3. INV-023 cross-file invariant `test_inv023_area_nplayer_coherence.py` 2/2 (still green after floor removal). |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **15 FIXED cumulative (ARITH-005/010/015/016/024/101/102/103/105/106/107/108/109/112/113), 17 N/A (ARITH-001/002/003/006/007/008/009/011/012/013/014/020/021/022/023/110/209), 14 ❌ MISSING remaining** (net change: +1 fixed, +4 N/A, −5 missing). |
| Branch | `master` — local 2.9.76 ahead of `origin/master` by **9 commits** (ARITH-005 fix + ARITH-209 reclass + prior handoff + ARITH-105 fix + ARITH-110 reclass + prior handoff + carry-counter cluster fix + ARITH-107 fix + level-0 dice cluster reclass). |

## Next Intended Task

1. **Push approval needed** — 9 commits ahead spanning
   2.9.70–2.9.76. Verify with `git log origin/master..HEAD`. The
   carry-counter, ARITH-107, and level-0 cluster work should ship
   together to avoid half-applied parity state.
2. **ARITH-111** — held-back item-shop haggle floor at
   `mud/commands/shop.py:822`. Needs the `deduct_cost`-with-
   negative-cost analysis described in the audit doc row 26.
   Reachable when `profit_buy < 50` (custom area shops); ROM
   allows `cost` to go negative while Python clamps to 0. Plan:
   probe `deduct_cost` in ROM `src/act_obj.c` (lines around the
   buy path) to determine whether ROM tolerates negative cost
   without UB, then either close as a real divergence or
   reclass with the divergence-but-bounded rationale.
3. **ARITH-114** — PC ceiling divergence on `get_curr_stat`
   (Python flat 25 vs ROM per-race/class `max_stat` at
   `src/handler.c:861-869`). Only matters above stat-22; can wait
   for a focused stat-table session.
4. **Remaining ARITH triage open**: 14 ❌ MISSING. The remaining
   MISSING entries are mostly higher-context (need downstream
   effect analysis, not single-line floor removals). Triage doc
   `docs/parity/audits/ARITHMETIC_BOUNDARY.md` has the list.
5. **Pre-existing lint** still parked: B007/F841 at 5 sites in
   `mud/skills/handlers.py` (672/1734/3469/3616/6249),
   `mud/handler.py:566-567,960`,
   `tests/integration/test_do_practice_command.py:255`,
   `mud/commands/combat.py:685`,
   `mud/commands/consumption.py:11,164-166`.
6. **GitNexus**: FTS read-only warnings fired repeatedly this
   session (documented upstream issue); node/edge graph remains
   current — stop-and-reindex fired after each commit and was
   honored, graph is fresh as of session end.
7. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
8. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
