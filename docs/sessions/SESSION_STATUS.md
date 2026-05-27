# Session Status — 2026-05-26 — PARALLEL Class 7 burn-down complete (2.9.57)

## Current State

- **Class 7 PARALLEL_REPRESENTATIONS burn-down complete.** Five more
  active hex-flag bugs closed (PARALLEL-002, -003a, -003b, -006) plus
  the two final cleanup items (PARALLEL-008 dead `.carrying` fallback,
  PARALLEL-011 stale `count_users` docstring).
- **Pre-fix wrong bits:**
  - `PARALLEL-002` (`player_config.py:76`): `IMM_SUMMON = 0x10` (bit 4) → canonical `DefenseBit.SUMMON = 1<<0`. NPC `nosummon` toggle modified the wrong immunity bit; NPC stayed actually-summonable.
  - `PARALLEL-003a` (`remaining_rom.py:211`): `ACT_GAIN = 0x00100000` (bit 20) → canonical `ActFlag.GAIN = 1<<27`. `do_gain` trainer-lookup did not recognize canonical trainers.
  - `PARALLEL-003b` (`remaining_rom.py:105`): `COMM_QUIET = 0x4` (bit 2) → canonical `CommFlag.QUIET = 1<<0`. `do_quiet` toggled wrong bit; disagreed with every other CommFlag.QUIET read.
  - `PARALLEL-006` (`imm_load.py:184, 194`): `ACT_NOPURGE = 0x2000` / `ITEM_NOPURGE = 0x40` (bits 13/6) → canonical `ActFlag.NOPURGE = 1<<21` / `ExtraFlag.NOPURGE = 1<<14`. NOPURGE-flagged NPCs/objects were purged anyway.
- **Audit hypothesis fully overturned**: the original PARALLEL audit
  classified these as ⚠️ DRIFT-RISK ("values are correct today"). In
  practice 8 of 9 flagged rows were active bugs. The body-only
  static-scan methodology systematically under-classified inline hex
  literals because it didn't compute canonical bit position from the
  IntEnum and compare.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS_CONTINUED.md](SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS_CONTINUED.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS.md](SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS.md),
  [SESSION_SUMMARY_2026-05-26_META_BURNDOWN_MATH001_PARALLEL010.md](SESSION_SUMMARY_2026-05-26_META_BURNDOWN_MATH001_PARALLEL010.md),
  [SESSION_SUMMARY_2026-05-26_META_AUDITS_CLASS_1_7_8.md](SESSION_SUMMARY_2026-05-26_META_AUDITS_CLASS_1_7_8.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.57 |
| Tests | 2253 integration passed pre-edit; 13 new regression cases pass post-fix across the 4 new test files. Full `pytest -q` not yet confirmed post-PARALLEL-003a/003b — re-run before push. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | 23 of ~20 enforced (unchanged) |
| Meta-audit progress | 4 of 8 META classes audited. **Class 7 PARALLEL_REPRESENTATIONS: burn-down COMPLETE** (9 of 9 ⚠️/❌ rows resolved; 8 turned out to be active bugs). Class 1 BROADCAST_COVERAGE: not started (29 ❌, helper-transitivity caveat). Class 8 MATH_AND_RNG burn-down: **MATH-001 closed**. |
| Branch | `master` — local 2.9.57 (3 unpushed commits since `origin/master`: `8d81ed84`, `8f21e015`, `6419b001` + a final session-doc/CHANGELOG/version chore commit to come) |

## Next Intended Task

1. **Finalize session chore commit** — add `pyproject.toml` 2.9.57 bump,
   `CHANGELOG.md` 2.9.57 entries, audit-doc row flips, and these session
   docs in one `chore(parity): session handoff — PARALLEL Class 7
   complete 2.9.57` commit.
2. **Confirm `pytest -q` clean** before push.
3. **Push approval** required for 2.9.57 (4 commits since this push).
4. **Class 1 BROADCAST_COVERAGE burn-down** (next active meta-audit
   surface). 29 ❌ rows in `audits/BROADCAST_COVERAGE.md`. Helper-
   transitivity caveat — many ❌ rows are likely false positives because
   door commands route through `world/movement.py` and combat skills
   route through `damage()`. **Before promoting each row to a
   gap-closer, verify helper coverage**; helper hits collapse rows to
   ✅ without a commit, misses become gap-closers.
   - **Top 3 ranked**: BCAST-disarm/trip/dirt/surrender; BCAST-goto-001/002
     (poofin/poofout); BCAST-invis-001 / BCAST-incognito-001.
5. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   — order-dependent shared-state failure. Probable root cause is
   `character_registry` state leakage breaking wiznet broadcast
   resolution.
6. **GitNexus refresh**: index now ~11 commits stale (last indexed
   `069f17f`). Run `npx gitnexus analyze --skip-agents-md` before any
   new probe.
7. **Worktree hygiene**: 5 locked agent worktrees in `.claude/worktrees/`
   — `a1b07201d504ce97b` (from earlier Class 1 session) plus four new
   ones created during this session's failed Haiku-isolation attempt
   (`a63c12791ddff689a`, `ab5d92d13841f9896`, `ab80cecdfe4efc29e`,
   `af52312960b77fb7f`). Investigate why `isolation: worktree` did not
   actually isolate the agents (they wrote to main master), then unlock
   + remove the stale worktrees.
8. **Remaining META classes** (when ready to audit more): Class 2
   ARITHMETIC_BOUNDARY (half-session), Class 3 GATE_CONSISTENCY
   (session), Class 4 TRIGGER_CALL_SITE_MIGRATION (half-session),
   Class 5 LIFECYCLE_STAGING (session+).
