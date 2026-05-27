# Session Status — 2026-05-27 — BCAST Class 1 burn-down (2.9.62)

## Current State

- **Active audit**: META Class 1 BROADCAST_COVERAGE burn-down — **substantially complete**.
  Every row in `docs/parity/audits/BROADCAST_COVERAGE.md` is now ✅ FIXED, ✅ COVERED,
  or ⚠️ Partial-blocked-by-stable-ID. The three remaining ⚠️ rows (BCAST-009/017/038)
  each point at a documented Blocked-rows entry (GROUP-001, ORDER-001, STEAL-001) with
  a known fix shape.
- **Last completed** (4th session of 2026-05-27, 6 commits):
  - **Fixes**: BCAST-034 (`do_pick` 3× TO_ROOM); BCAST-035 (`do_purge` TO_ROOM + 2×
    TO_NOTVICT with new `_notvict_broadcast` helper); BCAST-030 (`bash` skill 4 acts
    with pronoun substitution); CLONE-001 (LEVEL_ constants + ROM-correct trust
    ladder); BCAST-002 mob branch (`do_clone` TO_ROOM, unblocked by CLONE-001).
  - **Bulk reclassification**: 13 Class A rows flipped to ✅ COVERED via per-row probe
    pass (BCAST-006/010/021/022/023/024/028/031/032/033/036/037/039).
  - **3 new gap IDs filed durably**: GROUP-001 (do_group `.messages`-only delivery),
    ORDER-001 (do_order bypasses act() visibility gating + wrong word-position guard),
    STEAL-001 (_steal_failure `.messages`-only delivery).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_BURNDOWN.md](SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_BURNDOWN.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_BCAST_WIZLOAD_UNBLOCK.md](SESSION_SUMMARY_2026-05-27_BCAST_WIZLOAD_UNBLOCK.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_WIZIMM_PROBE_DISCIPLINE.md](SESSION_SUMMARY_2026-05-27_BCAST_WIZIMM_PROBE_DISCIPLINE.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md](SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md),
  [SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md](SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.62 |
| Tests | Full integration suite **2297/2297 + 3 documented skips in 77s** (run this session, +8 tests since 2.9.61). Full `pytest -q` still hangs past 15min on this machine (pre-existing). |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE, Watch list — ORDER-001 closure in this surface is a natural lead-in to promoting INV-027). |
| Meta-audit progress | **5 of 8 META classes audited.** Class 1 BROADCAST_COVERAGE burn-down: **complete bar 3 blocked rows** — every row is now ✅ FIXED, ✅ COVERED, or ⚠️ Partial pointing at a stable Blocked-rows gap ID (GROUP-001 / ORDER-001 / STEAL-001). Class 7 PARALLEL_REPRESENTATIONS: COMPLETE. Class 8 MATH_AND_RNG: MATH-001 closed. |
| Branch | `master` — local 2.9.62 ahead of `origin/master` by **6 commits**. |

## Next Intended Task

1. **Push approval required** — 6 commits to push, covers all of 2.9.62.
2. **GROUP-001 + STEAL-001 closure** — both share the `.messages` →
   `broadcast_room`/`send_to_char` fix shape used for BCAST-035 this
   session. Pair them as two consecutive gap-closer commits (~20 min
   each). Closes BCAST-009 + BCAST-038.
3. **ORDER-001 closure** — needs an `act()`-equivalent helper that does
   `can_see_character` gating, then route the order message through it.
   Higher value than just the visibility gate — establishes the pattern
   for future "manual format" → `act()`-style migrations. Also fixes the
   wrong word-position guard. Closes BCAST-017.
4. **After the three Blocked-row closures, BROADCAST_COVERAGE.md is fully
   ✅** — Class 1 META audit is complete; move on to Class 2
   ARITHMETIC_BOUNDARY (or another META class).
5. **INV-027 promotion** (ACT-INVIS-TRUST-GATE): `_can_witness(actor,
   witness)` helper threaded through `_act_room` and `broadcast_room`.
   ORDER-001 in step 3 is a natural lead-in.
6. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
7. **GitNexus reindex** still stale (last `069f17f`, now ~30+ commits
   behind). FTS index reported read-only/broken throughout this session.
   Run `npx gitnexus analyze --skip-agents-md` before next probe-heavy
   session.
8. **Worktree hygiene** — 5 locked worktrees in `.claude/worktrees/`.
9. **Remaining META classes** (after Class 1 finishes): Class 2
   ARITHMETIC_BOUNDARY, Class 3 GATE_CONSISTENCY, Class 4
   TRIGGER_CALL_SITE_MIGRATION, Class 5 LIFECYCLE_STAGING.
