# Session Status — 2026-05-26 — `do_slay` TO_VICT/TO_NOTVICT broadcasts (2.9.50)

## Current State

- **`SLAY-002` closed** (`e61eda5`, 2.9.50). `do_slay` was returning
  only the TO_CHAR string ("You slay X in cold blood!"); the victim
  and bystanders saw nothing. Added TO_VICT broadcast to the victim
  and TO_NOTVICT broadcast to every other room occupant, both before
  `raw_kill(victim)` removes the victim from the room. Mirrors ROM
  `src/fight.c:3282-3284`.
- **Slay/purge cluster complete**: SLAY-001 (raw_kill routing,
  2.9.48), PURGE-001 (extract_character routing, 2.9.49), and
  SLAY-002 (broadcasts, 2.9.50) together bring the immortal
  load/purge/slay surface to full ROM parity for the death pipeline
  and INV-020 cleanup chain.
- **Tests**: 1 new (`test_slay_broadcasts.py`). Full suite:
  **4772 passed, 4 skipped** in 1242s (slower wall-clock than
  baseline; likely system load).
- **INV budget at 23/~20** — unchanged.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_SLAY_BROADCASTS.md](SESSION_SUMMARY_2026-05-26_SLAY_BROADCASTS.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_PURGE_EXTRACT_CHARACTER_ROUTING.md](SESSION_SUMMARY_2026-05-26_PURGE_EXTRACT_CHARACTER_ROUTING.md),
  [SESSION_SUMMARY_2026-05-26_SLAY_RAW_KILL_ROUTING.md](SESSION_SUMMARY_2026-05-26_SLAY_RAW_KILL_ROUTING.md),
  [SESSION_SUMMARY_2026-05-26_INV020_DISCONNECT_LEG.md](SESSION_SUMMARY_2026-05-26_INV020_DISCONNECT_LEG.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.50 |
| Tests | **4772 passed, 4 skipped** (full suite, 1242s wall) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **23 of ~20 enforced** — unchanged |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.50 (1 commit pending push approval: `e61eda5`) |

## Next Intended Task

1. **Push approval** required for 2.9.50 (`e61eda5`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.50 to origin/master").
2. **GitNexus refresh** — index multiple commits stale. Run
   `npx gitnexus analyze --skip-agents-md` before next probe.
3. **Probe-then-scope candidates remaining**:
   - **Position-transition adjacency** — `update_pos` callers
     (do_yell, do_emote-while-down) could surface a missing
     transition beyond INV-016 / INV-019.
   - **Group-leader on logout vs persistence** — saved characters
     with `leader != self` reload with dangling pointer
     reconstituted from save format.
