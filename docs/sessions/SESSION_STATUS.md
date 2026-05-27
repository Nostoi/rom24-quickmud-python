# Session Status — 2026-05-27 — ARITH-001/002/003 UB-divisor reclass (2.9.68)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) filed in
  2.9.64; cumulative close-out through 2.9.68 has reclassified 8 of
  the 10 UB-divisor cluster gaps under the
  `docs/divergences/UB_DIVISORS.md` policy. ARITH-014 (registry
  rating) and ARITH-005 (level-0 PC in xp_compute) remain from the
  policy-doc cluster.
- **Last completed** (1 commit this session):
  - **`ARITH-001`** / **`ARITH-002`** / **`ARITH-003`** —
    reclassified ⛔ N/A under UB-divisor policy. All three are
    `max(1, max_hit)` divisor floors in mob-program code
    (`mud/mobprog.py:1108` hpcnt, `:1651` HPCT trigger) and
    damage-message code (`mud/combat/messages.py:115` dam_message).
    NPC-reachable: `mud/spawning/templates.py:170-172` floors
    `_roll_dice` at 0 (not 1), so a mob proto with degenerate
    `hit_dice = (0,0,0)` spawns with `max_hit == 0`. The
    `getattr(..., 1)` defaults at mobprog.py only fire when the
    attribute is missing entirely, not when it's literally 0 — so
    the floors are reachable. ROM-cite comments added at all three
    sites pointing to `UB_DIVISORS.md`. No production behavior
    change (comment-only edits to two `.py` files). Regressions:
    `tests/test_arith_max_hit_floor.py` (2/2), `tests/test_mobprog.py`
    (2/2), `tests/test_combat_messages.py` (2/2).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_001_002_003_RECLASS.md](SESSION_SUMMARY_2026-05-27_ARITH_001_002_003_RECLASS.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_ARITH_UB_DIVISOR_CLOSEOUT.md](SESSION_SUMMARY_2026-05-27_ARITH_UB_DIVISOR_CLOSEOUT.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md](SESSION_SUMMARY_2026-05-27_ARITH_COIN_AND_ZERO_XP.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md](SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md),
  [SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md](SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md](SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.68 |
| Tests | Area suites green (`test_arith_max_hit_floor` 2/2, `test_mobprog` 2/2, `test_combat_messages` 2/2, `test_character_advancement` 21/21). Full integration suite not re-run this session; 2.9.64 baseline was 2302/2302 + 3 documented skips in 84s. No production code changed this session (comment-only edits). |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **7 FIXED cumulative (ARITH-010/015/016/024/101/102/103), 10 N/A (ARITH-001/002/003/006/007/008/009/011/012/013), 29 ❌ MISSING remaining** (was 32 after 2.9.67). UB-divisor cluster remaining: ARITH-014 (registry rating), ARITH-005 (level-0 PC xp_compute reachability probe needed). |
| Branch | `master` — local 2.9.68 ahead of `origin/master` by **8 commits** (4 from 2.9.66 + ARITH-011/012 reclass + ARITH-006/007/008 reclass + 2.9.67 handoff + ARITH-001/002/003 reclass + this handoff once committed). |

## Next Intended Task

1. **Push approval needed** — 8 commits ahead for 2.9.68.
2. **Continue closing ARITH gaps** via `/rom-gap-closer`. Remaining
   UB-divisor cluster:
   - **ARITH-014** (`mud/skills/registry.py:330`,
     `max(1, multiplier * rating * 4)`) — rating == 0 means the skill
     has no class rating; check whether the upstream filter at
     `skill_table` actually prevents the divide. Likely dead-code
     N/A like ARITH-006/007/008. Quick probe.
   - **ARITH-005** (`mud/groups/xp.py:130`, `max(1, gch_level)`) —
     NOT dead code. The `max(1, ...)` changes `level_range =
     victim_level - 1` vs ROM's `victim_level - 0` for a level-0 PC.
     First loop at `:100-109` skips level≤0 from `total_levels`
     accumulation, but second loop at `:114-124` only skips NPCs, so
     a level-0 PC *does* reach `xp_compute`. Need a reachability
     probe on whether `level == 0` is reachable for a logged-in PC.
3. **ARITH-105 (get_curr_stat)** still the largest remaining ARITH
   gap. ROM uses `URANGE(3, perm+mod, max)` — minimum stat is **3**,
   not 0. Python floors at 0 (`mud/models/character.py:478`). High
   blast radius — every stat-dependent calc (hit/dam/AC/carry/wield/
   sneak). Plan for multiple commits or one careful commit with a
   comprehensive parametrized test across the affected paths.
4. **ARITH-209 spot-check** still pending (`mud/loaders/json_loader.py:357`
   — comment claims a ROM `max(1, arg4)` floor that may not exist).
5. **Pre-existing lint** still parked: `mud/handler.py:566-567` (F841),
   `mud/handler.py:960` (F401), `tests/integration/test_do_practice_command.py:255`
   (F841), `mud/commands/combat.py:685` (F541) — quick clean-ups
   available in passing.
6. **GitNexus**: stop-and-reindex rule fired once this session (after
   `0af47cf2`); reindex completed in background. FTS DB remains
   read-only at the MCP layer (documented upstream issue); node/edge
   graph is current.
7. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
8. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
