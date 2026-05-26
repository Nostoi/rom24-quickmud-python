# Session Status — 2026-05-26 — INV-020 void-quit cleanup-chain (2.9.46)

## Current State

- **INV-020 expanded to EXTRACT-CHAR-CLEANUP-CHAIN** (`c9b3937`, 2.9.46).
  ROM `src/handler.c:2117-2122 extract_char` requires every PC-extract
  trigger to call `nuke_pets + die_follower`. INV-020 originally locked
  only the raw_kill leg; the void-quit leg
  (`mud/game_loop.py:_auto_quit_character`) bypassed both, leaving
  charmed pets in the world with dangling `master` pointers and group
  followers with dangling `leader` pointers. Now wired through both
  cleanups. INV-020 row renamed; no new INV-NNN added per advisor
  guidance (same mechanism, different trigger).
- **Disconnect-cleanup leg still open**. `mud/net/connection.py`
  telnet+websocket `finally` blocks also bypass the chokepoint. Split
  off as a follow-up gap-closer pending small helper-extraction
  refactor (anonymous `finally` code is hard to test directly).
- **`affect_check` prototype walk** (`1ffc06f`, 2.9.45) and
  **`check_assist` misplacement** (`cf126f0`, 2.9.44, pushed) remain
  from this 2026-05-26 session series.
- **Tests**: 2 new (`test_inv020_extract_quit_cleanup.py`) on top of
  the 2 added in 2.9.45 and 3+1 added in 2.9.44. Full suite:
  **4771 passed, 4 skipped** in 542s.
- **INV budget at 23/~20** — unchanged (INV-020 expanded in place).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_INV020_EXTRACT_QUIT_CLEANUP.md](SESSION_SUMMARY_2026-05-26_INV020_EXTRACT_QUIT_CLEANUP.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_AFFECT_CHECK_PROTOTYPE_FALLBACK.md](SESSION_SUMMARY_2026-05-26_AFFECT_CHECK_PROTOTYPE_FALLBACK.md),
  [SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md](SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.46 |
| Tests | **4771 passed, 4 skipped** (full suite, 542s) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **23 of ~20 enforced** — INV-020 widened in place, count unchanged |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.46 (1 commit pending push approval: `c9b3937`) |

## Next Intended Task

1. **Push approval** required for 2.9.46 (`c9b3937`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.46 to origin/master").
2. **GitNexus refresh** — index stale at `5d3ce9d` (three commits
   behind: `cf126f0` 2.9.44, `1ffc06f` 2.9.45, `c9b3937` 2.9.46). Run
   `npx gitnexus analyze --skip-agents-md` before the next probe.
3. **Follow-up gap-closer**: INV-020 disconnect-cleanup leg.
   Extract `_disconnect_cleanup(char)` helper from
   `mud/net/connection.py` telnet+websocket `finally` blocks
   (lines 1989+, 2263+), route through `_nuke_pets + die_follower`,
   add 2 tests for that leg.
4. **Probe-then-scope candidates** (after disconnect-leg closes, INV
   budget 23/~20):
   - **TRIG_KILL / TRIG_DEATH dispatch** — engine.py audit notes
     wired correctly but no INV row pins it.
   - **Position-transition adjacency** — `update_pos` callers
     (do_yell, do_emote-while-down) could surface a missing
     transition beyond INV-016 / INV-019.
