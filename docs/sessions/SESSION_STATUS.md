# Session Status — 2026-05-26 — INV-026 violence-trigger dispatch scope (2.9.43)

## Current State

- **INV-026 VIOLENCE-TRIGGER-DISPATCH-SCOPE enforced** (`c48224af`).
  ROM `src/fight.c:60-99 violence_update` is the only site that
  fires TRIG_FIGHT / TRIG_HPCNT. Python now dispatches from
  `mud/game_loop.py:violence_tick` after `multi_hit` returns,
  guarded by `attacker.fighting is victim` (mirroring ROM's
  `(victim = ch->fighting) == NULL` re-fetch). Pre-INV-026 every
  caller of `multi_hit` (assist mobs, spec_funs, mob_cmds) wrongly
  fired both triggers — this was inherited from HPCNT-001's
  deliberately-shallow scoping decision. INV-026 completes that
  contract at the deeper ROM-correct layer.
- **`char.location` audit sweep closed** (`476084d5`). One real bug
  fixed (`do_eat`/EAT-004 broadcast had the same Affect-attribute
  typo cluster as `do_put`); five dead-code fallback sites
  stripped. The Character-typed `.location` typo cluster is now
  fully purged.
- **Tests**: 8 new INV-026 sweep tests, 2 rewritten HPCNT-001
  tests, 1 updated mobprog-triggers test. Full suite: **4760
  passed, 4 skipped** in 664s.
- **INV budget at 23/~20 enforced** — over by three after INV-026
  filed. INV-026 is its own contract (own ROM mechanism, own
  enforcement point), so no merge candidate. Future consolidation
  candidates: INV-016/019 (position transitions), INV-006/009
  (fighting-pointer + registry cleanup).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_INV026_VIOLENCE_TRIGGER_SCOPE.md](SESSION_SUMMARY_2026-05-26_INV026_VIOLENCE_TRIGGER_SCOPE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.43 |
| Tests | **4760 passed, 4 skipped** (full suite, 664s) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **23 of ~20 enforced** — over by three, within margin per AGENTS.md soft cap |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.43 (2 commits pending push approval) |

## Next Intended Task

1. **Close the `check_assist` misplacement** as a follow-up
   gap-closer. ROM `src/fight.c:90` calls `check_assist` from
   `violence_update` after `multi_hit` returns, not inside
   `multi_hit` (currently at `mud/combat/engine.py:317`). Same
   misplacement shape as INV-026; intentionally split for commit
   hygiene. Single-file move; no new INV row needed.
2. **GitNexus refresh** — index stale at `6b21fa9` (3 commits
   behind). Run `npx gitnexus analyze --skip-agents-md` before the
   next probe so impact-analysis numbers are accurate.
3. **Continue probe-then-scope at 23/~20**. Candidate areas not
   yet covered by an INV: affect ticks, mob script triggers
   beyond TRIG_FIGHT/HPCNT (TRIG_KILL/DEATH guards already wired
   correctly per the engine.py audit), group/follower chain.
   Methodology is still earning its keep — INV-026 was found by
   the same probe pattern that produced INV-014/INV-013 and the
   INV-025 sweep.
