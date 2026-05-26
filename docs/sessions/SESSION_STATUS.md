# Session Status — 2026-05-26 — INV-020 fully enforced (2.9.47)

## Current State

- **INV-020 fully enforced across all four PC-extract triggers**
  (`16a5d97`, 2.9.47). The disconnect-cleanup leg was the last open
  hole: socket close (`mud/net/connection.py` telnet+websocket
  `finally` blocks) bypassed `_nuke_pets + die_follower` even though
  it already treated the close as `do_quit` semantics per INV-009.
  Extracted a `_disconnect_extract_cleanup(char)` module-level helper
  and wired it into both `finally` blocks, gated on
  `not forced_disconnect` (reconnect transfers the live Character to
  a new descriptor — not an extract). Helper-extraction made the
  cleanup testable without standing up a real socket (advisor's
  blocking concern from 2.9.46 — resolved).
- **All four PC-extract triggers now funnel through the cleanup
  chain**: raw_kill (INV-020 original), void-quit auto-pull
  (`_auto_quit_character`, 2.9.46), `do_pull`-derived
  `_extract_character` (mob_cmds chokepoint), socket disconnect
  (2.9.47).
- **Tests**: 2 new (`test_disconnect_nukes_pets` +
  `test_disconnect_calls_die_follower`) extending the INV-020
  regression file to 4/4. Full suite: **4773 passed, 4 skipped** in
  464s.
- **INV budget at 23/~20** — unchanged (INV-020 widened in place
  across three sessions; no new INV-NNN rows).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_INV020_DISCONNECT_LEG.md](SESSION_SUMMARY_2026-05-26_INV020_DISCONNECT_LEG.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_INV020_EXTRACT_QUIT_CLEANUP.md](SESSION_SUMMARY_2026-05-26_INV020_EXTRACT_QUIT_CLEANUP.md),
  [SESSION_SUMMARY_2026-05-26_AFFECT_CHECK_PROTOTYPE_FALLBACK.md](SESSION_SUMMARY_2026-05-26_AFFECT_CHECK_PROTOTYPE_FALLBACK.md),
  [SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md](SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.47 |
| Tests | **4773 passed, 4 skipped** (full suite, 464s) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **23 of ~20 enforced** — INV-020 widened in place across 2.9.x sessions, count unchanged |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.47 (1 commit pending push approval: `16a5d97`) |

## Next Intended Task

1. **Push approval** required for 2.9.47 (`16a5d97`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.47 to origin/master").
2. **GitNexus refresh** — index stale at `069f17f` (2 commits behind:
   `c9b3937` 2.9.46, `16a5d97` 2.9.47). Run
   `npx gitnexus analyze --skip-agents-md` before the next probe.
3. **INV-020 is fully enforced** — close the row's open trail.
   Probe-then-scope candidates remaining (INV budget 23/~20):
   - **TRIG_KILL / TRIG_DEATH dispatch** — engine.py audit notes
     wired correctly but no INV row pins it; contract-lock more than
     bug find.
   - **Position-transition adjacency** — `update_pos` callers
     (do_yell, do_emote-while-down) could surface a missing transition
     beyond INV-016 / INV-019.
   - **Group-leader on logout vs persistence** — saved characters
     with `leader != self` reload with the dangling pointer
     reconstituted from save format; worth a probe.
