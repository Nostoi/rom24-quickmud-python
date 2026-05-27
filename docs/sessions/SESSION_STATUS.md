# Session Status — 2026-05-26 — `do_purge` _extract_character routing (2.9.49)

## Current State

- **`PURGE-001` closed** (`f71c422`, 2.9.49). `mud/commands/imm_load.py:do_purge`
  was calling the same stripped local `_extract_char` stub that
  `do_slay` used pre-2.9.48, at three call sites (room-purge loop,
  named-player, named-NPC). All three now route through
  `mud.mob_cmds._extract_character`, so the INV-020 cleanup chain
  (`nuke_pets` + `die_follower`) and inventory extraction run as
  ROM `src/handler.c:2103-2180 extract_char` requires. Removed the
  now-unused local stub.
- **INV-020 surface stabilization**: between 2.9.46 (void-quit leg),
  2.9.47 (disconnect leg), 2.9.48 (do_slay → raw_kill), and 2.9.49
  (do_purge → _extract_character), every PC-extract / NPC-extract
  trigger in immortal-command and lifecycle paths now funnels through
  the canonical chokepoint.
- **Tests**: 1 new (`test_purge_routes_through_extract_character.py`).
  Full suite: **4771 passed, 4 skipped** in 487s.
- **INV budget at 23/~20** — unchanged (same INV-020 contract; this
  fix just enrolls another caller).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_PURGE_EXTRACT_CHARACTER_ROUTING.md](SESSION_SUMMARY_2026-05-26_PURGE_EXTRACT_CHARACTER_ROUTING.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_SLAY_RAW_KILL_ROUTING.md](SESSION_SUMMARY_2026-05-26_SLAY_RAW_KILL_ROUTING.md),
  [SESSION_SUMMARY_2026-05-26_INV020_DISCONNECT_LEG.md](SESSION_SUMMARY_2026-05-26_INV020_DISCONNECT_LEG.md),
  [SESSION_SUMMARY_2026-05-26_INV020_EXTRACT_QUIT_CLEANUP.md](SESSION_SUMMARY_2026-05-26_INV020_EXTRACT_QUIT_CLEANUP.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.49 |
| Tests | **4771 passed, 4 skipped** (full suite, 487s) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **23 of ~20 enforced** — unchanged |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.49 (1 commit pending push approval: `f71c422`) |

## Next Intended Task

1. **Push approval** required for 2.9.49 (`f71c422`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.49 to origin/master").
2. **GitNexus refresh** — index stale at `069f17f` (5 commits behind).
   Run `npx gitnexus analyze --skip-agents-md` before next probe.
3. **Next gap-closer**: `do_slay` missing TO_VICT/TO_NOTVICT
   broadcasts (ROM `src/fight.c:3282-3284`). One-line fix returning
   the room-broadcast act messages alongside the existing TO_CHAR
   return value.
4. **Probe-then-scope candidates remaining**:
   - **Position-transition adjacency** — `update_pos` callers
     (do_yell, do_emote-while-down) could surface a missing transition
     beyond INV-016 / INV-019.
   - **Group-leader on logout vs persistence** — saved characters
     with `leader != self` reload with the dangling pointer
     reconstituted from save format.
