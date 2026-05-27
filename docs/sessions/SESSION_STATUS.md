# Session Status — 2026-05-27 — ARITH coin weights, zero-XP delivery, ARITH-009 reclass (2.9.66)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) was filed in
  2.9.64; this session closed 4 more gaps (one was a misdiagnosed
  reclass-then-file-then-fix loop) and reclassified one to N/A.
- **Last completed** (3 commits this session):
  - **`ARITH-009`** — reclassified ⛔ N/A. The `max(0, xp)` floor at
    `mud/groups/xp.py:257` is unreachable defensive code; `xp_compute`'s
    arithmetic has no path to a negative result. Original audit prose
    misdiagnosed the location.
  - **`ARITH-024`** — newly filed (real divergence the prose was groping
    at) and ✅ FIXED. `group_gain` now delivers the "You receive 0
    experience points." message and calls `gain_exp(gch, 0)`
    unconditionally, matching ROM `src/fight.c:1786-1789`. Pre-fix
    `if xp <= 0: continue` swallowed both when `xp_compute` returned 0.
  - **`ARITH-101`/`ARITH-102`/`ARITH-103`** — ✅ FIXED in one commit
    (sibling gaps in `create_money`). All three weight branches now use
    raw `c_div`, matching ROM `src/handler.c:2455`/`:2465`/`:2477`. Small
    coin stacks (1–4 gold, 1–19 silver, small mixed) now correctly weigh
    0 instead of 1.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md](SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md](SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md](SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md](SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.66 |
| Tests | Area suites green (xp/advancement/group_combat/combat_death 61/61 + 1 skip; money/drop/container/room/INV-014 76/76). Full integration suite not re-run this session; 2.9.64 baseline was 2302/2302 + 3 documented skips in 84s. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **7 FIXED cumulative (ARITH-010/015/016/024/101/102/103), 2 N/A (ARITH-009/013), 37 ❌ MISSING remaining** (was 42 after 2.9.65). |
| Branch | `master` — local 2.9.66 ahead of `origin/master` by **3 commits** (ARITH-009 reclass + ARITH-024 + ARITH-101/102/103; plus this session's handoff once committed). |

## Next Intended Task

1. **Push approval needed** — 3 + 1 handoff = 4 commits to push for 2.9.66.
2. **Continue closing ARITH gaps** via `/rom-gap-closer`. Suggested order:
   - **ARITH-011/012** (`mud/commands/combat.py:512/636`) — `max_hit` floor in berserk/flee hp%. Reachability probe first: berserk only gates on mana >= 50, not max_hit > 0. A char with max_hit == 0 reaching this code is theoretically possible but requires a corrupt/uninit character. Same shape as ARITH-013 (post-gate dead code) — needs character-init reachability check. If reachable, straightforward c_div fix; if not, reclass to N/A.
   - **ARITH-105** (`mud/models/character.py:478`) — `get_curr_stat` floors stats at 0; ROM uses `URANGE(3, perm+mod, max)`. **High blast radius** (every stat-dependent calc — hit/dam/AC/carry/wield/sneak); needs broad integration test coverage across multiple stat paths. Plan multiple commits or careful single commit with comprehensive parametrized test.
   - **ARITH-009 nearby cluster** — ARITH-005/006/007/008 (level-0 PC / total_levels=0 in xp_compute alignment branches) — UB-protection group, likely needs policy decision (assert + docs/divergences note rather than ROM replication).
3. **Decide UB-protection cluster policy** before closing ARITH-001/002/003/005/006/007/008/011/012/014. Likely `assert` + `docs/divergences/` note rather than direct ROM replication.
4. **ARITH-209 spot-check** still pending (`mud/loaders/json_loader.py:357` — comment claims a ROM `max(1, arg4)` floor that may not exist).
5. **Pre-existing lint** at `mud/handler.py:566-567` (F841 unused `where`, `vector`), `mud/handler.py:960` (F401 unused `Object` import), and `tests/integration/test_do_practice_command.py:255` (F841 unused `output`) — quick clean-ups available in passing.
6. **GitNexus**: stop-and-reindex rule active and honoured this session. FTS DB remains read-only at MCP layer (upstream issue per CLAUDE.md); node/edge graph is current after each reindex.
7. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
8. **Worktree hygiene** — locked worktrees still present in `.claude/worktrees/`.
