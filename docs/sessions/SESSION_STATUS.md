# Session Status — 2026-05-27 — BCAST Class 1 burn-down COMPLETE (2.9.63)

## Current State

- **Active audit**: META Class 1 BROADCAST_COVERAGE burn-down — **COMPLETE**.
  Every row in `docs/parity/audits/BROADCAST_COVERAGE.md` is now ✅ FIXED or
  ✅ COVERED. No ⚠️ Partial rows remain.
- **Last completed** (5th session of 2026-05-27, 3 gap-closer commits + handoff):
  - **`STEAL-001`** — `_steal_failure` TO_VICT/TO_NOTVICT now reach live sockets via new `_send_to_char_sync` helper. Closes BCAST-038.
  - **`GROUP-001`** — `do_group` add/remove TO_VICT/TO_NOTVICT now reach live sockets via the same helper. Closes BCAST-009.
  - **`ORDER-001`** — `do_order` TO_VICT now routes through `_pers_gated(actor, viewer)` (mirrors ROM `pers()`), gating `$n` on `can_see_character`. Wiz-invis orderers render as "someone" to low-trust followers. Also fixed pre-existing reversed-args/never-awaited `send_to_char` call. Closes BCAST-017.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md](SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_BURNDOWN.md](SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_BURNDOWN.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_WIZLOAD_UNBLOCK.md](SESSION_SUMMARY_2026-05-27_BCAST_WIZLOAD_UNBLOCK.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_WIZIMM_PROBE_DISCIPLINE.md](SESSION_SUMMARY_2026-05-27_BCAST_WIZIMM_PROBE_DISCIPLINE.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md](SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md),
  [SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md](SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.63 |
| Tests | Full integration suite **2302/2302 + 3 documented skips in 84s** (run this session, +5 tests since 2.9.62). Full `pytest -q` still hangs past 15min on this machine (pre-existing). |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE, Watch list — the new `_pers_gated` helper from ORDER-001 is a stepping-stone toward the wider `_can_witness(actor, witness)` thread-through). |
| Meta-audit progress | **5 of 8 META classes audited; Class 1 BROADCAST_COVERAGE now COMPLETE.** Class 7 PARALLEL_REPRESENTATIONS: COMPLETE. Class 8 MATH_AND_RNG: MATH-001 closed. |
| Branch | `master` — local 2.9.63 ahead of `origin/master` by **4 commits** (3 gap-closers + handoff). |

## Next Intended Task

1. **Push approval required** — 4 commits to push, covers all of 2.9.63.
2. **Promote INV-027 ACT-INVIS-TRUST-GATE.** The `_pers_gated` helper added
   this session for `do_order` is the simplest possible form of the wider
   contract. The cross-file fix is a `_can_witness(actor, witness)` helper
   threaded through `_act_room` and `broadcast_room` (per
   `CROSS_FILE_INVARIANTS_TRACKER.md`). Could fold `_pers_gated` into a
   shared `mud/utils/act.py` symbol when the wider promotion lands.
3. **Pick a new META class** — Class 1 is done. Candidates:
   - Class 2 ARITHMETIC_BOUNDARY (likely smallest follow-up — survey THAC0,
     damage caps, weight/carry rollover sites).
   - Class 3 GATE_CONSISTENCY (single-source of truth for trust ladders,
     position guards, can_drop/can_get/can_wear gates).
   - Class 4 TRIGGER_CALL_SITE_MIGRATION (mob_cmds / mob_progs invocation
     parity).
   - Class 5 LIFECYCLE_STAGING (room enter/exit ordering, save/load
     consistency).
4. **GitNexus reindex** still stale (last `069f17f`, now ~36 commits behind).
   FTS index reported read-only/broken throughout this session. Run
   `npx gitnexus analyze --skip-agents-md` before the next probe-heavy
   session.
5. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
6. **Worktree hygiene** — 5 locked worktrees in `.claude/worktrees/`.
