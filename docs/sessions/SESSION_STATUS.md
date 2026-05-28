# Session Status — 2026-05-27 — ARITH-111 close + ARITH-115 follow-on (2.9.77)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) filed in
  2.9.64; cumulative close-out through 2.9.77 has closed
  **16 FIXED** and **17 N/A** of the 47 triaged ARITH-NNN candidates
  (45 original + ARITH-024 post-triage + ARITH-114 + ARITH-115
  follow-ons). **14 ❌ MISSING remain**.
- **This session** (3 commits incl. handoff):
  - Pushed 9 accumulated commits (2.9.70–2.9.76) to
    `origin/master`.
  - **`ARITH-111`** — ✅ FIXED (2.9.77). Item-shop haggle
    `max(0, unit_price - discount)` clamp at
    `mud/commands/shop.py:822` removed. ROM
    `src/act_obj.c:2722-2729` does raw subtraction; when
    `shop.profit_buy < 50` (custom area shops) and the haggle roll
    wins, `cost` goes negative and `deduct_cost(ch, negative_cost)`
    refunds the player via `ch->silver -= silver` at ROM
    `src/handler.c:2410`. Python's `mud/handler.py:885`
    `deduct_cost` already mirrors that arithmetic for negative cost.
    Regression: `tests/integration/test_arith_111_haggle_no_floor.py`
    (1/1 — profit_buy=40, cost=100, roll=99 → unit_price = −9,
    player wealth 100 → 109).
  - **`ARITH-115`** — ❌ FILED (not closed). Surfaced during
    ARITH-111 close. Keeper-side bookkeeping
    `_set_keeper_total_wealth` / `_set_character_total_wealth`
    clamps at `mud/commands/shop.py:462,474` floor wealth at 0;
    ROM `src/act_obj.c:2747-2748` lets keeper gold drift negative
    on the refund path. Filed per AGENTS.md
    "out-of-scope-bugs-surface-mid-audit" rule as row 32 in the
    ARITH triage doc. Held back from ARITH-111 commit because the
    helpers serve both buy and sell paths.
  - Full integration suite: **2341 passed, 3 skipped** in 89.17s.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_111_HAGGLE_FLOOR.md](SESSION_SUMMARY_2026-05-27_ARITH_111_HAGGLE_FLOOR.md)
  (predecessors:
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
| Version | 2.9.77 |
| Tests | Full integration suite **2341 passed, 3 skipped** in 89.17s. ARITH-111 regression `test_arith_111_haggle_no_floor.py` 1/1. `tests/test_shops.py` 36/36 (no haggle-floor regressions). |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **16 FIXED cumulative (ARITH-005/010/015/016/024/101/102/103/105/106/107/108/109/111/112/113), 17 N/A (ARITH-001/002/003/006/007/008/009/011/012/013/014/020/021/022/023/110/209), 14 ❌ MISSING remaining** (47 total: 45 triaged + ARITH-024 post-triage + ARITH-114 + ARITH-115 follow-ons). |
| Branch | `master` — local 2.9.77 ahead of `origin/master` by **1 commit** (ARITH-111 fix). Handoff commit will make 2. |

## Next Intended Task

1. **Push approval needed** — 2.9.77 ARITH-111 commit + this
   handoff commit. Verify with `git log origin/master..HEAD`.
2. **ARITH-115** — keeper-side / character-side wealth clamps in
   `mud/commands/shop.py:462,474`. Companion divergence to
   ARITH-111. Closing test: same setup as ARITH-111 but with
   `keeper.gold = 0, keeper.silver = 0` so the refund drives
   keeper wealth below zero. Assert `keeper.silver < 0` (or
   `keeper.gold < 0`). Both helpers share the same ROM-mismatch
   pattern, so the floor can come out of both in one commit.
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
6. **GitNexus**: stop-and-reindex fired after the ARITH-111 commit
   and was honored — graph is fresh as of session end. FTS
   read-only warnings continued (documented upstream issue), but
   node/edge graph is current.
7. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
8. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
