# Session Status — 2026-05-27 — ARITH-105 fix + ARITH-110 reclass (2.9.72 + 2.9.73)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) filed in
  2.9.64; cumulative close-out through 2.9.73 has now closed
  **9 FIXED** and **13 N/A** of the 46 triaged ARITH-NNN candidates
  (45 original + 1 follow-on ARITH-114). All UB-divisor-cluster
  reachability probes resolved earlier in the day. **24 ❌ MISSING
  remain**.
- **Last completed** (2 commits this session):
  - **`ARITH-105`** — ✅ FIXED (`7b6bc45`, 2.9.72). `Character.
    get_curr_stat` now floors at 3 (`max(3, min(25, total))`),
    matching ROM `URANGE(3, perm+mod, max)` at `src/handler.c:872`.
    Pre-fix `max(0, ...)` allowed stacked debuffs to feed wrong-row
    reads of str_app / dex_app / con_app / int_app / wis_app.
    Side-effect: `test_advancement_con_app::
    test_advance_level_hp_minimum_floor_is_two` rewritten to verify
    the `UMAX(2, add_hp)` floor via `monkeypatch(con_hitp_bonus, -4)`
    instead of the now-impossible CON-0 path. Regression:
    `tests/integration/test_get_curr_stat_floor_three.py` (17/17).
    Full integration suite **2334 passed, 3 skipped**. Ceiling
    divergence at the same line filed as the new **ARITH-114**
    (Python flat 25 vs ROM per-race/class max).
  - **`ARITH-110`** — ⛔ N/A (`bf51a43`, 2.9.73). Pet-shop haggle
    floor at `mud/commands/shop.py:586` is mathematically
    unreachable. ROM `cost -= cost/2 * roll/100` with `roll ∈ [0, 99]`
    gives `discount < c_div(cost, 2)`, so `cost - discount > 0` for
    all `cost ≥ 0`. Same shape as ARITH-006/007/008/013/014. ROM-cite
    comment added at `mud/commands/shop.py:582-590`. **ARITH-111**
    (item-shop sibling) **NOT** reclassed — it is genuinely reachable
    when `profit_buy < 50` because the discount is derived from
    `obj->cost` but applied to the marked-up `unit_price`. Held back
    with documented reachability conditions for a future session that
    can analyze `deduct_cost` semantics under negative cost.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_105_AND_110.md](SESSION_SUMMARY_2026-05-27_ARITH_105_AND_110.md)
  (predecessors:
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
| Version | 2.9.73 |
| Tests | Full integration suite **2334 passed, 3 skipped** in 75.52s (run post-ARITH-105). Shop suite re-verified after ARITH-110 comment-only edit: 66 passed. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **9 FIXED cumulative (ARITH-005/010/015/016/024/101/102/103/105), 13 N/A (ARITH-001/002/003/006/007/008/009/011/012/013/014/110/209), 24 ❌ MISSING remaining** (was 26 at session start; net change: −1 ARITH-105 fixed, −1 ARITH-110 reclassed N/A, +1 ARITH-114 new = 24). |
| Branch | `master` — local 2.9.73 ahead of `origin/master` by **5 commits** (ARITH-005 fix + ARITH-209 reclass + prior session handoff + ARITH-105 fix + ARITH-110 reclass). |

## Next Intended Task

1. **Push approval needed** — 5 commits ahead for 2.9.70 / 2.9.71 /
   2.9.72 / 2.9.73 (verify with `git log origin/master..HEAD`).
2. **Carry-weight/number cluster** —
   ARITH-106/108/109/112/113 are **five sites of the same
   `obj_from_char` divergence** (`max(0, carry_weight - delta)` and
   `max(0, carry_number - 1)` floors that ROM does not have at
   `src/handler.c:1678-1679`). Likely closeable as one commit pattern
   like ARITH-101/102/103 did for `create_money`. Strategy: probe
   ROM `obj_from_char` for any hidden upstream guard, write one
   parametrized test exercising double-extract / over-subtract paths
   at all five sites, drop the five floors in one commit.
3. **Level-0 spell/skill dice cluster** — ARITH-020/021/022/023.
   Reachable via mob-program or scripted dispatch per the audit doc;
   probe ROM source first to see whether each is a real divergence
   or dead defensive code.
4. **ARITH-111** when ready — the held-back item-shop haggle floor.
   Needs the `deduct_cost`-with-negative-cost analysis described in
   the audit doc row 26 (when `profit_buy < 50`, max discount
   `≈ proto.cost / 2` can exceed `unit_price = proto.cost *
   profit_buy / 100`).
5. **ARITH-114** — the new PC-ceiling divergence on `get_curr_stat`
   (Python flat 25 vs ROM per-race/class `max_stat` for PCs at
   `src/handler.c:861-869`). Lower priority than the level-0 /
   carry-tracking clusters because it only matters above stat-22.
6. **Pre-existing lint** still parked: `mud/handler.py:566-567` (F841),
   `mud/handler.py:960` (F401), `tests/integration/test_do_practice_command.py:255`
   (F841), `mud/commands/combat.py:685` (F541). Pre-existing pyright
   diagnostics in `mud/commands/shop.py` (lines 81/86/212/216/261/220/328)
   confirmed unchanged by this session's edits.
7. **GitNexus**: stop-and-reindex rule fired twice this session
   (after `7b6bc45` and `bf51a43`); both reindexes completed in
   background. FTS DB remains read-only at the MCP layer (documented
   upstream issue); node/edge graph is current.
8. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
9. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
