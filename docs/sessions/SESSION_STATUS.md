# Session Status — 2026-05-27 — BCAST door-command burn-down (2.9.59)

## Current State

- **Active audit**: META Class 1 BROADCAST_COVERAGE burn-down (in
  progress). Door-command cluster complete this session.
- **Last completed**: BCAST-016, BCAST-003, BCAST-013, BCAST-027
  (4 door-command fixes, 13 new broadcasts) + BCAST-004, BCAST-005,
  BCAST-026 (3 false-positive collapses, audit-doc only).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md](SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md](SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md),
  [SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS_CONTINUED.md](SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS_CONTINUED.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.59 |
| Tests | Integration suite 2270 passed / 3 documented skips (2:13). 14 new regression cases (4 files) added this session and pass. Full `pytest -q` hung past 15min on this machine — killed; integration suite is the right surface per AGENTS.md. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | 23 of ~20 enforced (unchanged); INV-024 candidate VISIBILITY-TRANSITION-BROADCAST-ORDERING still at 2 instances |
| Meta-audit progress | **5 of 8 META classes audited.** Class 1 BROADCAST_COVERAGE burn-down: **11 of 29 ❌ rows resolved** since opening in 2.9.58 (7 fixed, 4 false-positive collapses). 18 ❌ + 10 ⚠️ rows remain (out of 209 ✅ baseline). Class 7 PARALLEL_REPRESENTATIONS: COMPLETE. Class 8 MATH_AND_RNG: MATH-001 closed. |
| Branch | `master` — local 2.9.59 (4 gap-fix commits + 1 chore commit to come) ahead of `origin/master` by 5 commits |

## Next Intended Task

1. **Finalize session chore commit** — `pyproject.toml` 2.9.59 bump,
   `CHANGELOG.md` 2.9.59 section, BROADCAST_COVERAGE.md row flips
   (BCAST-003, 004, 005, 013, 016, 026, 027), session docs in one
   `chore(parity): session handoff — BCAST door-command burn-down
   2.9.59` commit.
2. **Push approval** required for 2.9.59 (5 commits to push).
3. **Wiz/immortal probe** — BCAST-002 `clone`, BCAST-014 `mload`,
   BCAST-015 `oload`, BCAST-018 `quit`, BCAST-020 `report`,
   BCAST-029 `violate`. Mostly 1-2 ROM acts each — likely cheap
   real gap-closers. Probe pattern: parallel Sonnet subagent reads
   each ROM C function + Python handler, returns COVERED/PARTIAL/
   REAL GAP per row.
4. **Combat real-gap closer** — BCAST-007 `envenom` (2 acts,
   `src/act_obj.c:820`). Single gap-closer commit.
5. **Movement / position commands** (BCAST-006 `enter`, BCAST-021-024
   `rest`/`sit`/`sleep`/`stand`) — the most expensive remaining BCAST
   rows by act count (5-12 each). Consider a probe-then-scope pass
   before attempting; some may also be partially covered by
   `mud/world/movement.py` helpers.
6. **Shop commands** — BCAST-028 `value` (4 TO_VICT, real gap), plus
   ⚠️ partial closures for BCAST-031 `buy` (3/9) and BCAST-037 `sell`
   (2/5).
7. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   — still unresolved.
8. **GitNexus reindex** still stale (last `069f17f`); now ~20 commits
   behind. MCP FTS index reported read-only/broken throughout this
   session — `gitnexus_impact` was unreliable, so falls back to `grep`
   + integration-suite-as-blast-radius were used per CLAUDE.md known-
   gap section. Run `npx gitnexus analyze --skip-agents-md` before the
   next probe session.
9. **Worktree hygiene**: 5 locked worktrees in `.claude/worktrees/`
   from prior sessions. Investigate then unlock + remove.
10. **Remaining META classes**: Class 2 ARITHMETIC_BOUNDARY,
    Class 3 GATE_CONSISTENCY, Class 4 TRIGGER_CALL_SITE_MIGRATION,
    Class 5 LIFECYCLE_STAGING.
