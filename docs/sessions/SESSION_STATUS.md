# Session Status — 2026-05-26 — `check_assist` dispatch scope (2.9.44)

## Current State

- **`check_assist` misplacement closed** (`cf126f0`). ROM
  `src/fight.c:90` calls `check_assist` from `violence_update` after
  `multi_hit` returns; Python had it embedded inside `multi_hit`, so
  every direct caller (`mud/combat/assist.py` recursive round,
  `mud/spec_funs.py` spec_cast paths, `mud/mob_cmds.py` mob `kill`)
  provoked another assist round. Lifted to
  `mud/game_loop.py:violence_tick` before the NPC trigger dispatch,
  mirroring ROM's `check_assist → IS_NPC → TRIG_FIGHT/TRIG_HPCNT`
  ordering. Two re-reads of `attacker.fighting is victim` guard the
  dispatch — once after `multi_hit` (victim-died), once after
  `check_assist` (helper-landed-killing-blow). Folded under INV-026 in
  the tracker (no new INV-NNN — both contracts share `src/fight.c:60-99
  violence_update`). The combat-trigger contract is now fully
  ROM-correct.
- **Tests**: 3 new (`tests/integration/test_check_assist_dispatch_scope.py`),
  1 rewritten (`tests/test_combat_assist.py::TestAssistIntegration` —
  was asserting ROM-contradicting `multi_hit`-direct behavior). Full
  suite: **4767 passed, 4 skipped** in 666s.
- **INV budget at 23/~20** — unchanged. The `check_assist` close
  folded into INV-026 rather than spawning a new row.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md](SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.44 |
| Tests | **4767 passed, 4 skipped** (full suite, 666s) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **23 of ~20 enforced** — over by three, within margin per AGENTS.md soft cap |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.44 (1 commit pending push approval: `cf126f0`) |

## Next Intended Task

1. **GitNexus refresh** — index stale at `5d3ce9d` (one commit behind
   after `cf126f0`). Run `npx gitnexus analyze --skip-agents-md` before
   the next probe so impact numbers reflect the new state.
2. **Continue probe-then-scope at 23/~20 INV budget**. Combat-trigger
   contract is now fully ROM-correct (no more deferred items in this
   area). Candidate probe areas not yet covered by an INV:
   - **Affect ticks** — `mud/handler.py:affect_update` /
     `Character.affect_remove` cross-module contracts beyond INV-015
     (wear-off message ordering, follower-charm-expiry race).
   - **PC-quit follower/pet cleanup** — INV-020 covers raw_kill;
     adjacent `nuke_pets` / `stop_follower(pet)` chain on quit may
     have a gap.
   - **TRIG_KILL / TRIG_DEATH dispatch** — engine.py audit notes
     they're correctly wired but no INV row pins it.
3. **Push approval required** before `2.9.44` reaches origin/master.
   Per standing rule: do NOT push without explicit per-cluster
   approval ("yes push v2.9.44 to origin/master").
