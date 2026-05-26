# Session Status — 2026-05-26 — INV-023 + INV-024 enforced; INV-025 candidate filed (2.9.39)

## Current State

- **INV-023 (AREA-NPLAYER-COHERENCE)** enforced 2.9.37 (`d8c1b6c`). Fixed
  `do_recall` bypassing `area.nplayer` accounting — every cross-area recall
  was leaving the source area falsely occupied. Routes through
  `Room.add_character`/`remove_character`. ROM `src/handler.c:1491-1568`.
- **INV-024 (CONTAINER-CLOSED-VISIBILITY)** enforced 2.9.38 (`cc3f8c7`).
  Fixed `do_get` reading CONT_CLOSED off the prototype instead of the
  OBJ_DATA instance — every freshly-spawned closed container had a
  transparent lid to `get all`. Four-surface contract pinned (get / put /
  look in / examine). ROM `src/act_obj.c:291-295`, `src/act_info.c:1160-1162`.
- **INV-025 candidate (MOBPROG-ACT-TRIGGER-DISPATCH)** filed 2.9.39
  (`935b373`). Real gap: ROM `act()` fires `mp_act_trigger` for every NPC
  recipient with TRIG_ACT — Python dispatches only via speech. Not closed:
  ROM's `MOBtrigger` recursion guard has no Python equivalent; wiring
  dispatch without porting the guard would re-enter on TRIG_ACT responses
  that call `act()` themselves. Scope = audit-then-implement. Watch list
  entry in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-26_INV023_INV024_INV025_CANDIDATE.md](SESSION_SUMMARY_2026-05-26_INV023_INV024_INV025_CANDIDATE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.39 |
| Tests | 2212 passed, 3 skipped (full integration suite, last green at 2.9.38; 2.9.39 is docs-only) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | 24 of ~20 enforced + 1 candidate; INV-001 … INV-024 ✅ ENFORCED, INV-025 filed |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` (up to date with origin) — pushed through `935b373` |

## Next Intended Task

**Close INV-025 properly** (multi-commit audit-then-implement):

1. Port ROM's `MOBtrigger` global (`src/comm.c:311`) to `mud/mobprog.py`
   as a thread-local flag or context manager. Toggle FALSE inside `do_mob`
   and any recursive path mirroring `src/act_obj.c:832-836` /
   `src/mob_cmds.c:333-335`.
2. Wire `mp_act_trigger` dispatch into `broadcast_room` (or the correct
   delivery layer — deliberate choice between `act_format` /
   `broadcast_room` / `_push_message`; INV-015's lesson is that the wrong
   layer doubles or skips delivery).
3. Add `tests/integration/test_inv025_mobprog_act_trigger_dispatch.py`
   with one case for normal dispatch and one for the recursion guard.
4. Flip Watch list → enforced row. Budget hits 25/~20, tripping
   consolidation-or-restructure threshold from AGENTS.md.

If consolidation becomes necessary at 25: four obvious dual pairs are
documented in the tracker footer (INV-014/021 creation/extract,
INV-015/018 affect-lifecycle/wear-off, INV-023/010 PC-movement under
ROOM-PEOPLE-COHERENCE umbrella, INV-001/002 message-delivery duals).

GitNexus index is stale (last indexed `bd7952b`, three commits behind).
Run `npx gitnexus analyze --skip-agents-md` at the start of the next
session before relying on `gitnexus_impact` / `gitnexus_context`.
