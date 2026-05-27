# Session Status — 2026-05-27 — ARITH UB-divisor close-out (2.9.67)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) filed in
  2.9.64; cumulative close-out through 2.9.67 has reclassified 5 of the
  10 UB-divisor cluster gaps and established the policy doc that
  unblocks the remaining 5.
- **Last completed** (2 commits this session):
  - **`ARITH-011`** / **`ARITH-012`** — reclassified ⛔ N/A. The
    `max(1, max_hit)` floors at `mud/commands/combat.py:512` (do_berserk)
    and `:636` (do_flee) are deliberate Python divergences from ROM
    `src/fight.c:2310` and `src/act_move.c` do_flee respectively. ROM
    divides `100 * ch->hit / ch->max_hit` raw and tolerates SIGFPE (one
    process); Python cannot, because `ZeroDivisionError` would crash
    the game loop for every connected player. New policy doc
    `docs/divergences/UB_DIVISORS.md` formalizes this for the broader
    UB-divisor cluster. Regression: `tests/test_arith_max_hit_floor.py`
    (2/2).
  - **`ARITH-006`** / **`ARITH-007`** / **`ARITH-008`** — reclassified
    ⛔ N/A. The `max(1, total_levels)` floors at `mud/groups/xp.py:166`
    / `:170` / `:174` (three alignment branches of `xp_compute`) are
    dead defensive code: the upstream guard at `xp.py:111-112` floors
    `total_levels` to `max(1, ch.level)` before any call to
    `xp_compute` at `:117`. Same shape as ARITH-013 — post-gate dead
    code, not a UB-policy keeper. ROM-cite comment added.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_UB_DIVISOR_CLOSEOUT.md](SESSION_SUMMARY_2026-05-27_ARITH_UB_DIVISOR_CLOSEOUT.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md](SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md](SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md](SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md](SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.67 |
| Tests | Area suites green (`test_arith_max_hit_floor` 2/2 new; `test_skill_combat_rom_parity` + `test_flee_moves_character` 105/105; `test_advancement` + `test_character_advancement` 40/40). Full integration suite not re-run this session; 2.9.64 baseline was 2302/2302 + 3 documented skips in 84s. No production code changed this session. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **7 FIXED cumulative (ARITH-010/015/016/024/101/102/103), 7 N/A (ARITH-006/007/008/009/011/012/013), 32 ❌ MISSING remaining** (was 37 after 2.9.66). New policy doc `docs/divergences/UB_DIVISORS.md` lights up the path for the remaining UB-divisor cluster (ARITH-001/002/003/014). |
| Branch | `master` — local 2.9.67 ahead of `origin/master` by **7 commits** (4 from 2.9.66 + ARITH-011/012 reclass + ARITH-006/007/008 reclass + this handoff once committed). |

## Next Intended Task

1. **Push approval needed** — 7 commits ahead for 2.9.67.
2. **Continue closing ARITH gaps** via `/rom-gap-closer`. With the
   UB-divisor policy in place, the remaining UB cluster is fast:
   - **ARITH-001/002/003** (`max_hit`/`max_mana`/`max_move` floors) —
     same shape as ARITH-011/012; quick reachability probe each, expect
     N/A reclass with ROM-cite comment.
   - **ARITH-014** (`mud/skills/registry.py:330`,
     `max(1, multiplier * rating * 4)`) — rating == 0 is upstream-filtered
     by `skill_table` (skill is not registered without a class rating);
     likely dead-code N/A like ARITH-006/007/008.
3. **ARITH-005** needs separate analysis. The `gch_level` floor at
   `mud/groups/xp.py:130` is *not* dead code (`max(1, ...)` changes
   `level_range = victim_level - 1` vs ROM's `victim_level - 0` for a
   level-0 PC). The first `group_gain` loop at `:100-109` skips
   level≤0 members from `total_levels` accumulation, but the second
   loop at `:114-124` only skips NPCs, so a level-0 PC *does* reach
   `xp_compute`. Need a reachability probe on whether `level == 0` is
   itself reachable for a logged-in PC.
4. **ARITH-105 (get_curr_stat)** still the largest remaining ARITH gap.
   ROM uses `URANGE(3, perm+mod, max)` — minimum stat is **3**, not 0.
   Python floors at 0 (`mud/models/character.py:478`). High blast radius
   — every stat-dependent calc (hit/dam/AC/carry/wield/sneak). Plan
   for multiple commits or one careful commit with a comprehensive
   parametrized test across the affected paths.
5. **ARITH-209 spot-check** still pending (`mud/loaders/json_loader.py:357`
   — comment claims a ROM `max(1, arg4)` floor that may not exist).
6. **Pre-existing lint** still parked: `mud/handler.py:566-567` (F841),
   `mud/handler.py:960` (F401), `tests/integration/test_do_practice_command.py:255`
   (F841), `mud/commands/combat.py:685` (F541) — quick clean-ups
   available in passing.
7. **GitNexus**: stop-and-reindex rule fired twice this session
   (after `b5526d03` and after `fb8d97d2`); both reindexes completed
   in the background before the next commit. FTS DB remains read-only
   at the MCP layer (documented upstream issue); node/edge graph is
   current.
8. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
9. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
