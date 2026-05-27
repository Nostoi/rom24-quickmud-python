# Session Status — 2026-05-27 — ARITH-005 fix + ARITH-209 reclass (2.9.70 + 2.9.71)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) filed in
  2.9.64; cumulative close-out through 2.9.71 has now closed
  **8 FIXED** and **12 N/A** of the 45 triaged ARITH-NNN candidates.
  All UB-divisor-cluster reachability probes from the original triage
  are now resolved. **26 ❌ MISSING remain** — ARITH-105
  (`get_curr_stat`) is the largest remaining gap.
- **Last completed** (2 commits this session):
  - **`ARITH-005`** — ✅ FIXED (`9a894117`, 2.9.70). Removed the
    `gch_level = max(1, ...)` floor at `mud/groups/xp.py:130`.
    ROM `xp_compute` (`src/fight.c:1818-1819`) uses `gch->level` raw
    and relies on the final `xp = xp * gch->level / divisor` to return
    0 naturally for a level-0 PC; the floor masked that path. Real
    reachability via `Character.level: int = 0` default + level-0
    test helper + `group_gain` second loop only skipping NPCs.
    Regression: `tests/integration/test_xp_compute_level_zero_pc.py`
    (2/2). Full integration suite **2317 passed, 3 skipped**.
  - **`ARITH-209`** — ⛔ N/A (`2231b670`, 2.9.71). Spot-check of
    the `json_loader.py:357` floor confirmed ROM has no floor on
    P-reset `arg4` (`db.c:1040-1044 load_resets` and `db.c:1788
    reset_room`), and no shipped area file uses `arg4 == 0` (77 P
    resets, all `arg4 == 1`). Inaccurate "mirrors ROM" comment was
    replaced with accurate ROM-cites at both Python sites
    (`json_loader.py:357-359` + `reset_handler.py:665`). No
    production behavior change.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_005_AND_209.md](SESSION_SUMMARY_2026-05-27_ARITH_005_AND_209.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_ARITH_001_002_003_RECLASS.md](SESSION_SUMMARY_2026-05-27_ARITH_001_002_003_RECLASS.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_UB_DIVISOR_CLOSEOUT.md](SESSION_SUMMARY_2026-05-27_ARITH_UB_DIVISOR_CLOSEOUT.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md](SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md](SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md](SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md](SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.71 |
| Tests | Full integration suite **2317 passed, 3 skipped** in 75.38s (run post-ARITH-005). Area/reset/spawn suite re-verified after ARITH-209 comment-only edits: 162 passed. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **8 FIXED cumulative (ARITH-005/010/015/016/024/101/102/103), 12 N/A (ARITH-001/002/003/006/007/008/009/011/012/013/014/209), 26 ❌ MISSING remaining** (was 28 after 2.9.69). |
| Branch | `master` — local 2.9.71 ahead of `origin/master` by **2 commits** (ARITH-005 fix + ARITH-209 reclass). |

## Next Intended Task

1. **Push approval needed** — 2 commits ahead for 2.9.70 + 2.9.71.
2. **ARITH-105 (`get_curr_stat`)** — the largest remaining ARITH gap.
   ROM uses `URANGE(3, perm + mod, max)` — minimum stat is **3**,
   not 0. Python floors at 0 (`mud/models/character.py:478`). High
   blast radius — every stat-dependent calc (hit/dam/AC/carry/wield/
   sneak). Strategy: single parametrized integration test exercising
   `STR/DEX/CON/INT/WIS` at stat=0/1/2/3 boundaries across
   hit/dam/AC/carry derived stats, then change the floor.
3. **ARITH triage remaining**: 26 ❌ MISSING after this session
   (was 28 at session start). After ARITH-105 the next-easiest probes
   are likely in the Batch B/C rows of
   `docs/parity/audits/ARITHMETIC_BOUNDARY.md` that haven't been
   touched yet.
4. **Pre-existing lint** still parked: `mud/handler.py:566-567` (F841),
   `mud/handler.py:960` (F401), `tests/integration/test_do_practice_command.py:255`
   (F841), `mud/commands/combat.py:685` (F541) — quick clean-ups
   available in passing. New pyright/B010 diagnostics in
   `mud/spawning/reset_handler.py` and `mud/loaders/json_loader.py`
   surfaced as PostToolUse output this session — all pre-existing,
   not introduced (verified by `git stash` round-trip).
5. **GitNexus**: stop-and-reindex rule fired twice this session
   (after `9a894117` and `2231b670`); both reindexes completed in
   background. FTS DB remains read-only at the MCP layer (documented
   upstream issue); node/edge graph is current.
6. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
7. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
