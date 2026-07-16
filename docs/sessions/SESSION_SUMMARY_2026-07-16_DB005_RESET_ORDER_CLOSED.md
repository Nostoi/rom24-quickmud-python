# Session Summary — 2026-07-16 — DB-005 closed (reset processing order: per-room ascending room-vnum)

## Scope

Autonomous loop iteration 1/10. Picked up the "Next Intended Task" from the
prior status: **DB-005**, the highest-value open gap (boot-world parity —
Python applied area resets in .are FILE order; ROM `reset_area` walks rooms in
ascending room-vnum order, each room owning its reset list). Single
gap-closer session per `/rom-gap-closer DB-005`.

## Outcomes

### `DB-005` — ✅ FIXED

- **Python**: `mud/spawning/reset_handler.py:apply_resets` (+ new
  `_reset_owner_room_vnum`, `_room_ordered_resets` helpers)
- **ROM C**: `src/db.c:2003-2015` (`reset_area`), `src/db.c:980-1108`
  (`load_resets`/`new_reset` room attachment: M/O own `arg3`, P/G/E inherit
  the previous reset's room, D/R use `arg1`), `src/db.c:1647-1657`
  (`reset_room` locals `LastMob`/`LastObj`/`level`/`last`)
- **Gap**: DB-005 — reset processing order diverged (file order vs per-room
  ascending room-vnum), diverging world population wherever a global M-limit
  binds mid-area (valley.are 7803: 4 sentries vs ROM's 3) AND boot creation
  order (`char_list`/`character_registry` global order for multi-instance
  protos — silently desyncing INV-045 newest-first walks cross-engine).
- **Fix**: `apply_resets` now buckets `area.resets` per owning room using
  ROM's `load_resets` rVnum-tracking rule and processes buckets in ascending
  room-vnum order (intra-room file order preserved). Reset state
  (`last_mob`/`last_obj`/`last_mob_level`/`last_reset_succeeded`) resets at
  every room boundary, mirroring `reset_room`'s locals — state can no longer
  leak across rooms.
- **Tests**:
  `tests/test_db_resets_rom_parity.py::test_reset_processing_order_room_vnum_ascending`
  (failing-first; valley-7803 shape: middle-vnum room skipped when a
  lower-vnum spawn binds the global limit, creation order asserted room-vnum
  ascending via `character_registry`, and a G-reset asserted to ride its
  file-preceding M into the correct room bucket).
- **Commit**: `29e9f99d`.

## Files Modified

- `mud/spawning/reset_handler.py` — per-room bucketing + ascending-vnum
  processing + per-room state reset
- `tests/test_db_resets_rom_parity.py` — new DB-005 regression test
- `docs/parity/DB_C_AUDIT.md` — DB-005 row flipped ⚠️ OPEN → ✅ FIXED
- `CHANGELOG.md` — `Fixed` entry for DB-005
- `pyproject.toml` — 2.14.322 → 2.14.323

## Test Status

- `tests/test_db_resets_rom_parity.py` — 36/36 passing
- Spawning/reset/differential suites — 146/146 passing (differential 98/98
  unchanged-green: goldens are C-engine output and the C already processed in
  room-vnum order, so the fix improves cross-engine convergence)
- Full suite: **6219 passed, 4 skipped, 0 failed** (286s parallel). The
  audit-predicted "file-order test/golden fallout" turned out to be zero —
  no shipped test encoded file-order populations.

## Notes

- The DB-005 row suggested also locking with a diff-harness `__mob_census`
  scenario over `valley.are`; the C-side goldens require the instrumented C
  binary to regenerate, so that scenario authoring is deferred to a
  C-capture-enabled session (the Python-side regression test covers the
  contract; existing 98/98 differential tests remain the cross-engine guard).

## Next Steps

Per the outstanding list: **FIGHT-098** (`mob_hit` OFF_AREA_ATTACK sweep,
sibling of FIGHT-095 with a proven fix pattern) is the next best-scoped gap;
GL-050 (aggr victim selection) needs a probe first. HANDLER-009 (test-only)
and carry-overs (FIGHT-094, DESC-001, OLC spell-name lookup, IS_BUILDER,
stray db files) remain.
