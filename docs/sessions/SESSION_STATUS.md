# Session Status — 2026-05-27 — BCAST WIZLOAD-001 unblock + 3 BCAST closures (2.9.61)

## Current State

- **Active audit**: META Class 1 BROADCAST_COVERAGE burn-down (in progress).
- **Last completed**:
  - **Fixes**: WIZLOAD-001 (4 layered name typos in wiz-load/clone surface);
    BCAST-014 `do_mload` TO_ROOM; BCAST-015 `do_oload` TO_ROOM;
    BCAST-002 obj branch `do_clone` TO_ROOM.
  - **COVERED collapse**: BCAST-019 `do_reply` (delegates to `do_tell`).
  - **New bug filed**: CLONE-001 — `do_clone` mob branch imports
    non-existent `LEVEL_AVATAR`/`LEVEL_DEMI`/`LEVEL_GOD` constants;
    blocks BCAST-002 mob branch.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_BCAST_WIZLOAD_UNBLOCK.md](SESSION_SUMMARY_2026-05-27_BCAST_WIZLOAD_UNBLOCK.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_BCAST_WIZIMM_PROBE_DISCIPLINE.md](SESSION_SUMMARY_2026-05-27_BCAST_WIZIMM_PROBE_DISCIPLINE.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md](SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md),
  [SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md](SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.61 |
| Tests | Full integration suite **2289/2289 + 3 documented skips in 87s** (run this session, +19 tests since 2.9.59). Full `pytest -q` still hangs past 15min on this machine (pre-existing). |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE, Watch list). |
| Meta-audit progress | **5 of 8 META classes audited.** Class 1 BROADCAST_COVERAGE burn-down: **24 of 29 ❌ rows resolved or routed since 2.9.58 opening** (11 fixed, 8 COVERED collapses, 1 ⚠️ Partial obj-fixed/mob-blocked, 0 ⚠️ BLOCKED remaining, 4 deferred). 5 ❌ + 10 ⚠️ remain (out of 209 ✅ baseline). Class 7 PARALLEL_REPRESENTATIONS: COMPLETE. Class 8 MATH_AND_RNG: MATH-001 closed. |
| Branch | `master` — local 2.9.61 ahead of `origin/master` by **8 commits** (4 from 2.9.60 + 4 from 2.9.61). |

## Next Intended Task

1. **Push approval required** — 8 commits to push, covers 2.9.60 + 2.9.61.
2. **CLONE-001 closure** — add missing `LEVEL_AVATAR`/`LEVEL_DEMI`/`LEVEL_GOD`
   constants without renaming existing `LEVEL_IMMORTAL=52` (wide blast
   radius), gate `do_clone` mob branch against a locally-defined ROM-
   aligned trust ladder. ~30 lines + the deferred BCAST-002 mob-branch
   test. Unblocks BCAST-002 mob branch closure (one more TO_ROOM emit).
3. **Then BCAST-002 mob branch** — standard `rom-gap-closer`, one
   TO_ROOM emit at `do_clone` mob branch end.
4. **Other viable BCAST real gaps** (cheap, 1-2 broadcasts each):
   BCAST-017 `do_order`, BCAST-010 `do_gtell`, BCAST-028 `do_value`.
   Verify BCAST-009 `do_group` — `group_commands.py` has zero broadcast
   helper calls per this session's probe, so likely a real gap despite
   2.9.20 session note claiming a fix.
5. **Expensive remaining BCAST** (large act counts, defer): BCAST-006
   `enter` (5), BCAST-021-024 `rest`/`sit`/`sleep`/`stand` (4-12 each).
6. **⚠️ Partial BCAST closures** (BCAST-030 through 039) — bulk pass
   when ❌ list is exhausted.
7. **INV-027 promotion** (ACT-INVIS-TRUST-GATE): `_can_witness(actor,
   witness)` helper threaded through `_act_room` and `broadcast_room`.
8. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
9. **GitNexus reindex** still stale (last `069f17f`); now ~28 commits
   behind. FTS index reported read-only/broken throughout this session.
   Run `npx gitnexus analyze --skip-agents-md` before next probe session.
10. **Worktree hygiene** — 5 locked worktrees in `.claude/worktrees/`.
11. **Remaining META classes**: Class 2 ARITHMETIC_BOUNDARY,
    Class 3 GATE_CONSISTENCY, Class 4 TRIGGER_CALL_SITE_MIGRATION,
    Class 5 LIFECYCLE_STAGING.
