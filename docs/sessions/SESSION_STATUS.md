# Session Status — 2026-05-26 — BCAST Class 1 burn-down opening (2.9.58)

## Current State

- **Class 1 BROADCAST_COVERAGE burn-down opened.** Three real gaps
  closed plus one false-positive row pair collapsed:
  - `BCAST-025` (`do_surrender`): added TO_VICT + TO_NOTVICT broadcasts.
  - `BCAST-012` (`do_invis`): fixed all three TO_ROOM broadcasts —
    wording divergence on toggle-off, silent drop via
    `can_see_character` on toggle-on, missing level-set branch.
  - `BCAST-011` (`do_incognito`): added toggle-off and level-set
    broadcasts.
  - `BCAST-001` / `BCAST-008` (`@goto` / `do_goto`): false positive —
    covered by `_act_room` helper; audit-doc row reclassified to
    ✅ COVERED (no commit).
- **Helper-transitivity discovery**: `_act_room` enforces
  `can_see_character` per recipient, so any visibility-transition
  broadcast emitted AFTER the visibility field is committed gets
  silently dropped. Fix pattern: broadcast BEFORE the field commit
  on fade-out / cloak-on, AFTER on fade-in / uncloak. Candidate
  cross-file invariant `INV-024
  VISIBILITY-TRANSITION-BROADCAST-ORDERING` — track if a third
  instance appears.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md](SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS_CONTINUED.md](SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS_CONTINUED.md),
  [SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS.md](SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.58 |
| Tests | 7 new regression cases (3 files) pass post-fix. Full `pytest -q` started in bg; confirm before push. Adjacent suites green (78 combat/surrender, 34 invis/imm_display). |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | 23 of ~20 enforced (unchanged); INV-024 candidate noted |
| Meta-audit progress | **5 of 8 META classes audited.** Class 1 BROADCAST_COVERAGE burn-down **opened**: 4 of 29 ❌ rows resolved (3 fixed, 1 pair collapsed). 25 ❌ + 10 ⚠️ rows remain (out of 209 ✅ baseline). Class 7 PARALLEL_REPRESENTATIONS: COMPLETE. Class 8 MATH_AND_RNG: MATH-001 closed. |
| Branch | `master` — local 2.9.58 (3 commits + 1 chore commit to come) ahead of `origin/master` by 4 commits |

## Next Intended Task

1. **Finalize session chore commit** — `pyproject.toml` 2.9.58 bump,
   `CHANGELOG.md` 2.9.58 entries, BROADCAST_COVERAGE.md row flips,
   session docs in one `chore(parity): session handoff — BCAST
   Class 1 burn-down opening 2.9.58` commit.
2. **Confirm `pytest -q` clean** before push.
3. **Push approval** required for 2.9.58.
4. **Combat-skill BCAST probe** (BCAST-004 `do_dirt`, BCAST-005
   `do_disarm`, BCAST-026 `do_trip`) — read `mud/combat/engine.py`'s
   `damage`/`one_hit` and verify whether the skill-specific
   TO_VICT/TO_NOTVICT strings ("$n shoves you backwards", "$n trips
   you", etc.) are emitted there. If yes → ✅ COVERED row flip
   without commit. If no → real gap-closers, ~2 broadcasts each.
5. **Door command BCAST probe** (BCAST-003 close, BCAST-013 lock,
   BCAST-016 open, BCAST-027 unlock) — likely covered by
   `mud/world/movement.py`; verify before promoting.
6. **Movement/position commands** (BCAST-006 enter, BCAST-021-024
   rest/sit/sleep/stand) — large ROM act counts (5-12 per command),
   likely the most expensive remaining rows.
7. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   — still unresolved.
8. **GitNexus reindex** still stale (last `069f17f`); now ~15 commits
   behind. Run `npx gitnexus analyze --skip-agents-md` before next
   probe.
9. **Worktree hygiene**: 5 locked worktrees in `.claude/worktrees/`
   from prior sessions. Investigate why `isolation: worktree` didn't
   isolate; then unlock + remove.
10. **Remaining META classes**: Class 2 ARITHMETIC_BOUNDARY,
    Class 3 GATE_CONSISTENCY, Class 4 TRIGGER_CALL_SITE_MIGRATION,
    Class 5 LIFECYCLE_STAGING.
