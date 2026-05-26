# Session Status — 2026-05-26 — `do_slay` raw_kill routing (2.9.48)

## Current State

- **`SLAY-001` closed** (`f4da2a7`, 2.9.48). `mud/commands/imm_load.py:do_slay`
  was calling a stripped local `_extract_char` stub instead of
  `raw_kill`, so slain NPCs vanished with no corpse, no death_cry, no
  gold drop, and no INV-020 cleanup (charmed pets and group followers
  leaked dangling pointers). Fix: replaced the stub call with
  `raw_kill(victim)` so the full ROM `src/fight.c:3285` pipeline runs.
- **Surfaced during TRIG_KILL / TRIG_DEATH dispatch probe** — the
  main combat dispatch (`engine.py:520-602`) matched ROM cleanly; the
  slay routing gap was the only finding. ROM `do_slay` deliberately
  skips TRIG_DEATH (calls `raw_kill` directly), so this is not a
  trigger-dispatch gap — it's a code-path divergence.
- **Adjacent gaps deferred** (carrying forward):
  - `do_purge` uses the same stripped stub at 3 call sites
    (lines 187, 216, 220 in `imm_load.py`). Same INV-020-touching
    leak. Next gap-closer candidate.
  - `do_slay` missing TO_VICT/TO_NOTVICT broadcasts (ROM
    `src/fight.c:3282-3284`).
- **Tests**: 1 new (`test_slay_routes_through_raw_kill.py`). Full
  suite: **4774 passed, 4 skipped** in 457s.
- **INV budget at 23/~20** — unchanged (single-function intra-module
  fix; no new INV-NNN).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_SLAY_RAW_KILL_ROUTING.md](SESSION_SUMMARY_2026-05-26_SLAY_RAW_KILL_ROUTING.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_INV020_DISCONNECT_LEG.md](SESSION_SUMMARY_2026-05-26_INV020_DISCONNECT_LEG.md),
  [SESSION_SUMMARY_2026-05-26_INV020_EXTRACT_QUIT_CLEANUP.md](SESSION_SUMMARY_2026-05-26_INV020_EXTRACT_QUIT_CLEANUP.md),
  [SESSION_SUMMARY_2026-05-26_AFFECT_CHECK_PROTOTYPE_FALLBACK.md](SESSION_SUMMARY_2026-05-26_AFFECT_CHECK_PROTOTYPE_FALLBACK.md),
  [SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md](SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.48 |
| Tests | **4774 passed, 4 skipped** (full suite, 457s) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **23 of ~20 enforced** — unchanged |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.48 (1 commit pending push approval: `f4da2a7`) |

## Next Intended Task

1. **Push approval** required for 2.9.48 (`f4da2a7`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.48 to origin/master").
2. **GitNexus refresh** — index stale at `069f17f`. Run
   `npx gitnexus analyze --skip-agents-md` before the next probe.
3. **Next gap-closer (priority)**: `do_purge` INV-020 leak — 3 call
   sites to the same stripped `_extract_char` stub, all need routing
   through the proper chokepoint (`mud/mob_cmds.py:_extract_character`
   or a thin shared helper that runs nuke_pets + die_follower). Same
   gap shape as SLAY-001 but split into its own commit per
   one-gap-one-test-one-commit.
4. **Follow-up after purge**: `do_slay` missing TO_VICT/TO_NOTVICT
   broadcasts (ROM `src/fight.c:3282-3284`).
5. **Probe-then-scope candidates remaining**:
   - **Position-transition adjacency** — `update_pos` callers
     (do_yell, do_emote-while-down) could surface a missing transition
     beyond INV-016 / INV-019.
   - **Group-leader on logout vs persistence** — saved characters
     with `leader != self` reload with the dangling pointer
     reconstituted from save format.
