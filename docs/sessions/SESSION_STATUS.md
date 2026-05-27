# Session Status — 2026-05-27 — First ARITH gap closures (2.9.65)

## Current State

- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY — **CLOSE-OUT in progress**.
  Triage doc (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`) was filed
  in 2.9.64; this session closed the first 3 high-impact gaps and
  reclassified one to N/A.
- **Last completed** (4 gap-closer / docs commits this session):
  - **`ARITH-015`** — berserk now passes raw `level/8` to `number_fuzzy`, matching ROM `src/fight.c:2333`.
  - **`ARITH-016`** — charm_person now passes raw `level/4` to `number_fuzzy`, matching ROM `src/magic.c:1383`.
  - **`ARITH-013`** — reclassified ⛔ N/A (dead-code post-gate at `mud/commands/combat.py:765-770`).
  - **`ARITH-010`** — do_practice now uses `c_div(gain_rate, rating)` raw, matching ROM `src/act_info.c:2772-2774`.
  - Also: **CLAUDE.md** strong stop-and-reindex rule when GitNexus reports stale.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md](SESSION_SUMMARY_2026-05-27_ARITH_FIRST_CLOSURES.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md](SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md),
  [SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md](SESSION_SUMMARY_2026-05-27_BCAST_CLASS1_COMPLETE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.65 |
| Tests | Area suites green (do_practice 17/17, berserk 1/1, charm 1/1, spell_casting + skills_integration 41/41 + 1 skip). Full integration suite not re-run; 2.9.64 baseline was 2302/2302 + 3 skips in 84s. Full `pytest -q` still hangs past 15min (pre-existing). |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE) — unchanged. |
| Meta-audit progress | 6 of 8 META classes complete or triaged. Class 2 ARITHMETIC_BOUNDARY close-out: **3 fixed (ARITH-010/015/016), 1 reclassified N/A (ARITH-013), 42 ❌ MISSING remaining** (was 45). |
| Branch | `master` — local 2.9.65 ahead of `origin/master` by **5 commits** (CLAUDE.md rule + 3 fixes + 1 reclass; plus this session's handoff once committed). |

## Next Intended Task

1. **Push approval needed** — 5 + 1 handoff = 6 commits to push for 2.9.65.
2. **Continue closing ARITH gaps** via `/rom-gap-closer`. Suggested order:
   - **ARITH-009** (`mud/groups/xp.py:257`) — `max(0, xp)` swallows ROM's negative XP returns from edge-case alignment math.
   - **ARITH-105** (`mud/models/character.py:478`) — `get_curr_stat` floors stats at 0; ROM uses `URANGE(3, perm+mod, max)`. High blast radius (every stat-dependent calc); needs careful test coverage and probably integration tests across multiple stat paths.
   - **ARITH-101/102/103** (`mud/handler.py:995/1003/1011`) — coin-weight inflation for small stacks. Three siblings, likely a single close pattern using `c_div`.
   - **ARITH-011/012** — `max_hit` floor in berserk/flee hp%. Suspect dead-code post-gate (similar to ARITH-013); needs reachability check first.
3. **Decide UB-protection cluster policy** before closing ARITH-001/002/003/005/006/007/008/011/012/014. Likely `assert` + `docs/divergences/` note rather than direct ROM replication.
4. **ARITH-209 spot-check** still pending (`mud/loaders/json_loader.py:357` — comment claims a ROM `max(1, arg4)` floor that may not exist).
5. **Pre-existing lint** at `tests/integration/test_do_practice_command.py:255` (F841 unused `output`) — quick clean-up.
6. **GitNexus**: stop-and-reindex rule active. FTS DB remains read-only at MCP layer (upstream issue per CLAUDE.md); node/edge graph is current after each reindex.
7. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
8. **Worktree hygiene** — 5 locked worktrees in `.claude/worktrees/`.
