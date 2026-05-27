# Session Status — 2026-05-27 — ARITH carry-counter cluster (2.9.74)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) filed in
  2.9.64; cumulative close-out through 2.9.74 has now closed
  **14 FIXED** and **13 N/A** of the 46 triaged ARITH-NNN candidates
  (45 original + 1 follow-on ARITH-114). **19 ❌ MISSING remain**.
- **Last completed** (1 commit this session, 5 gap IDs):
  - **`ARITH-106` / `ARITH-108` / `ARITH-109` / `ARITH-112` / `ARITH-113`**
    — ✅ FIXED (2.9.74). All five `obj_from_char` carry-counter floors
    removed in one commit:
    - `mud/models/character.py:580` — `Character.remove_object`
      carry_number floor (ARITH-106). `_recalculate_carry_weight()` still
      runs after, so the weight side stays coherent via fresh sum.
    - `mud/commands/obj_manipulation.py:638-640` — `_obj_from_char`
      carry_weight + carry_number floors (ARITH-108/109).
    - `mud/commands/consumption.py:347-351` — `_destroy_object`
      carry_weight + carry_number floors (ARITH-112/113).

    Now matches ROM `src/handler.c:1678-1679` bare subtraction.
    Regression: `tests/integration/test_obj_from_char_no_floor.py` (3/3).
    Full integration suite: **2337 passed, 3 skipped** in 85.66s.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_CARRY_COUNTER_CLUSTER.md](SESSION_SUMMARY_2026-05-27_ARITH_CARRY_COUNTER_CLUSTER.md)
  (predecessors:
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
| Version | 2.9.74 |
| Tests | Full integration suite **2337 passed, 3 skipped** in 85.66s. Cluster regression `test_obj_from_char_no_floor.py` 3/3. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **14 FIXED cumulative (ARITH-005/010/015/016/024/101/102/103/105/106/108/109/112/113), 13 N/A (ARITH-001/002/003/006/007/008/009/011/012/013/014/110/209), 19 ❌ MISSING remaining** (net change: −5 fixed). |
| Branch | `master` — local 2.9.74 ahead of `origin/master` by **7 commits** (ARITH-005 fix + ARITH-209 reclass + prior handoff + ARITH-105 fix + ARITH-110 reclass + prior handoff + **carry-counter cluster fix**). |

## Next Intended Task

1. **Push approval needed** — 7 commits ahead for 2.9.70 / 2.9.71 /
   2.9.72 / 2.9.73 / 2.9.74 (verify with `git log origin/master..HEAD`).
2. **ARITH-107** — `area.nplayer` floor at `mud/models/room.py:171` in
   `char_from_room` (`max(0, current - 1)` where ROM does raw
   `--ch->in_room->area->nplayer` at `src/handler.c:1502`). Same shape
   as today's cluster — likely one-commit closure if no upstream guard
   exists. Probe ROM `char_from_room` for any defensive guard first.
3. **Level-0 spell/skill dice cluster** — ARITH-020/021/022/023.
   Reachable via mob-program or scripted dispatch per the audit doc;
   probe ROM source first to see whether each is a real divergence
   or dead defensive code.
4. **ARITH-111** when ready — the held-back item-shop haggle floor.
   Needs the `deduct_cost`-with-negative-cost analysis described in
   the audit doc row 26 (when `profit_buy < 50`, max discount
   `≈ proto.cost / 2` can exceed `unit_price = proto.cost *
   profit_buy / 100`).
5. **ARITH-114** — the PC-ceiling divergence on `get_curr_stat`
   (Python flat 25 vs ROM per-race/class `max_stat` for PCs at
   `src/handler.c:861-869`). Lower priority than the level-0 /
   nplayer clusters because it only matters above stat-22.
6. **Pre-existing lint** still parked: `mud/handler.py:566-567` (F841),
   `mud/handler.py:960` (F401), `tests/integration/test_do_practice_command.py:255`
   (F841), `mud/commands/combat.py:685` (F541), plus
   `mud/commands/consumption.py:11` (Position unused) and `:164-166`
   (I001) seen this session — all pre-existing, untouched.
7. **GitNexus**: FTS index read-only warnings fired repeatedly this
   session (documented upstream issue); node/edge graph remains
   current. No reindex required — the warning is about FTS-table
   writes, not graph staleness.
8. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
9. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
