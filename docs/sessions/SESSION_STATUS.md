# Session Status — 2026-05-26 — `do_restore` affect_strip (2.9.51)

## Current State

- **`RESTORE-001` closed** (`21c92b8`, 2.9.51). `_restore_char` in
  `mud/commands/imm_load.py` was only refilling vitals; ROM
  `src/act_wiz.c:2807, 2839, 2861` strips plague/poison/blindness/
  sleep/curse at every restore path. Added the five `strip_affect`
  calls before vitals reset.
- **Immortal command cluster (2.9.48–2.9.51)**: SLAY-001 (raw_kill
  routing), PURGE-001 (extract_character routing), SLAY-002
  (TO_VICT/TO_NOTVICT broadcasts), RESTORE-001 (affect_strip) —
  every immortal command in `imm_load.py` (load, mload, oload,
  restore, slay, purge) now matches ROM contract on the
  side-effect surface.
- **Tests**: 1 new (`test_restore_strips_affects.py`). Integration
  suite: **2239 passed, 3 skipped** in 72s. (Full suite skipped this
  commit — RESTORE-001 is low-blast-radius helper-only.)
- **INV budget at 23/~20** — unchanged.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_RESTORE_AFFECT_STRIP.md](SESSION_SUMMARY_2026-05-26_RESTORE_AFFECT_STRIP.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_SLAY_BROADCASTS.md](SESSION_SUMMARY_2026-05-26_SLAY_BROADCASTS.md),
  [SESSION_SUMMARY_2026-05-26_PURGE_EXTRACT_CHARACTER_ROUTING.md](SESSION_SUMMARY_2026-05-26_PURGE_EXTRACT_CHARACTER_ROUTING.md),
  [SESSION_SUMMARY_2026-05-26_SLAY_RAW_KILL_ROUTING.md](SESSION_SUMMARY_2026-05-26_SLAY_RAW_KILL_ROUTING.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.51 |
| Tests | **2239 passed, 3 skipped** (integration only, 72s) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **23 of ~20 enforced** — unchanged |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.51 (1 commit pending push approval: `21c92b8`) |

## Next Intended Task

1. **Push approval** required for 2.9.51 (`21c92b8`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.51 to origin/master").
2. **GitNexus refresh** — index multiple commits stale. Run
   `npx gitnexus analyze --skip-agents-md` before next probe.
3. **Probe-then-scope candidates remaining**:
   - **Position-transition adjacency** — `update_pos` callers
     (do_yell, do_emote-while-down).
   - **Group-leader on logout vs persistence** — saved characters
     with `leader != self` reload with dangling pointer
     reconstituted from save format.
