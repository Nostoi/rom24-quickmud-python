# Session Status — 2026-05-31 — In-Game Bug Fixes (training, mana, room flags)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted), but
  this session was an **in-game-bug triage detour** — bugs the user found by
  playing, verified against ROM C, closed via the gap-closer loop.
- **Last completed**:
  - **NANNY-015 (2.11.60)** — new PC starts with 3 training sessions, not 18
    (`train_value()` had ported ROM's dead `nanny.c:684` formula instead of the
    `nanny.c:776` hardcoded 3).
  - **TRAIN-002 (2.11.60)** — training any stat costs 1 session, not 2 for
    non-prime (ROM `do_train` has no `else cost=2`).
  - **CAST-008 (2.11.60)** — failed spell cast costs half mana, not 1.5×
    (Python deducted full upfront + half on fail; ROM does either/or).
  - **TRAIN-003 (2.11.60)** — `train` requires an ACT_TRAIN mob in the room
    (gate was commented out behind a stale TODO).
- **Filed, deferred**: **DB-001 / INV-032** — room flags dropped game-wide
  (`room_loader.py:41` parses the wrong token; all 52 area JSONs have 0 flags).
  Its own session — see Next Intended Task.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-31_INGAME_BUGS_TRAIN_CAST.md](SESSION_SUMMARY_2026-05-31_INGAME_BUGS_TRAIN_CAST.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.60 |
| Tests | 5099 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 31 enforced (INV-001..031) + INV-032 ❌ OPEN (deferred) |
| Open correctness gaps | DB-001 (room flags), INV-032 (room-flags-survive-load) |
| Active focus | DB-001 room-flags fix (next session) |

## Next Intended Task

**Highest priority: DB-001 / INV-032 — room flags dropped game-wide** (its own
session). Steps:

1. Fix `mud/loaders/room_loader.py` room-flag parsing: discard `tokens[0]`
   (area number), `convert_flags_from_letters(tokens[1], RoomFlag)` for flags,
   `int(tokens[2])` for sector; assert `len(tokens) == 3` so malformed lines
   fail loud. Failing test first: load a known `.are` room, assert `ROOM_DARK`.
2. Regenerate all 52 `data/areas/*.json` via `mud/scripts/convert_are_to_json.py`
   (proven safe this session — all 52 regenerate byte-identical with the current
   loader, so only `flags` will change after the fix; no hand-edits to clobber).
3. Triage the test-suite fallout when ROOM_SAFE / ROOM_NO_RECALL / ROOM_DARK /
   ROOM_LAW activate game-wide. Some failing tests will be legitimately wrong
   (asserted flagless behavior — test bugs per AGENTS.md); some may be real
   ripples. Triage, do not blanket-update.
4. Write `tests/integration/test_inv032_room_flags_survive_load.py` (boot data,
   assert school "Darkened Room" vnum 3720 is dark at runtime) and flip INV-032
   to ✅ ENFORCED.
5. While in the loader: verify whether **exit/door flags** have the same loss
   (the converter only decodes the `locks` field via `_locks_to_exit_bits`).

Secondary: file/close `get_max_train` hardcoded-22 divergence (candidate
TRAIN-004 in `ACT_MOVE_C_AUDIT.md`). Then resume the cross-file invariants
probe pass (do_close/do_lock/do_unlock/do_pick INV-025 act-dispatch slices).
