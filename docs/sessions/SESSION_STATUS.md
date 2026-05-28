# Session Status — 2026-05-27 — ARITH-115 close (2.9.78)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) filed in
  2.9.64; cumulative close-out through 2.9.78 has closed
  **17 FIXED** and **17 N/A** of the 47 triaged ARITH-NNN candidates
  (45 original + ARITH-024 post-triage + ARITH-114 + ARITH-115
  follow-ons). **13 ❌ MISSING remain**.
- **Last completed**: **`ARITH-115`** — ✅ FIXED (2.9.78). Keeper-side
  and character-side wealth helpers (`_set_keeper_total_wealth` /
  `_set_character_total_wealth`) at `mud/commands/shop.py:461,473`
  no longer floor `total` at 0, and now split via `c_div`/`c_mod`
  instead of Python `//`/`%`. ROM `src/act_obj.c:2747-2748` adds
  keeper gold/silver raw — on the ARITH-111 player-refund branch
  (`profit_buy < 50` + winning haggle → negative `cost`) with a
  near-broke keeper, ROM lets keeper wealth drift below zero. ROM's
  only safety net is `deduct_cost`'s end-of-function rebalance at
  `src/handler.c:2412-2421` (character side only; already mirrored at
  `mud/handler.py:918-923`). Regression:
  `tests/integration/test_arith_115_keeper_wealth_no_floor.py` (1/1 —
  profit_buy=40, cost=100, roll=99, keeper at 0 wealth → drifts to −9).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_115_KEEPER_WEALTH_FLOOR.md](SESSION_SUMMARY_2026-05-27_ARITH_115_KEEPER_WEALTH_FLOOR.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_ARITH_111_HAGGLE_FLOOR.md](SESSION_SUMMARY_2026-05-27_ARITH_111_HAGGLE_FLOOR.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_107_AND_LEVEL_ZERO_CLUSTER.md](SESSION_SUMMARY_2026-05-27_ARITH_107_AND_LEVEL_ZERO_CLUSTER.md),
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
| Version | 2.9.78 |
| Tests | Full integration suite **2342 passed, 3 skipped** in 87.45s. ARITH-115 regression `test_arith_115_keeper_wealth_no_floor.py` 1/1. `tests/test_shops.py` 36/36 (no wealth-floor regressions). ARITH-111 regression still 1/1. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **17 FIXED cumulative (ARITH-005/010/015/016/024/101/102/103/105/106/107/108/109/111/112/113/115), 17 N/A (ARITH-001/002/003/006/007/008/009/011/012/013/014/020/021/022/023/110/209), 13 ❌ MISSING remaining** (47 total: 45 triaged + ARITH-024 post-triage + ARITH-114 + ARITH-115 follow-ons). |
| Branch | `master` — local 2.9.78 ahead of `origin/master` by **3 commits** (2.9.77 ARITH-111 fix, 2.9.77 handoff, 2.9.78 ARITH-115 fix). This handoff commit will make 4. |

## Next Intended Task

1. **Push approval needed** — 3 (soon 4) commits ahead of
   `origin/master`, shipping 2.9.77 + 2.9.78. Verify with
   `git log origin/master..HEAD`.
2. **ARITH-114** — PC ceiling divergence on `get_curr_stat`
   (Python flat 25 vs ROM per-race/class `max_stat` at
   `src/handler.c:861-869`). Only matters above stat-22; best
   handled in a focused stat-table session.
3. **Remaining ARITH triage open**: 13 ❌ MISSING. The remaining
   MISSING entries are mostly higher-context (need downstream
   effect analysis, not single-line floor removals). Triage doc
   `docs/parity/audits/ARITHMETIC_BOUNDARY.md` has the list.
4. **Pre-existing lint** still parked: B007/F841 at 5 sites in
   `mud/skills/handlers.py` (672/1734/3469/3616/6249),
   `mud/handler.py:566-567,960`,
   `tests/integration/test_do_practice_command.py:255`,
   `mud/commands/combat.py:685`,
   `mud/commands/consumption.py:11,164-166`. Plus two pre-existing
   F541 (extraneous `f` prefix) in `mud/commands/shop.py:798` area.
5. **GitNexus**: stop-and-reindex fired after the ARITH-115 commit
   and was honored — graph reindexed (40,918 nodes / 68,585 edges).
   FTS read-only / 32KB scope-extraction warnings continued
   (documented upstream issue), but node/edge graph is current at
   HEAD `3e94e6b`.
6. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
7. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
