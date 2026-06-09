# Session Summary — 2026-06-09 — FINDING-026 room people order

## Scope

Continued from `SESSION_SUMMARY_2026-06-09_HARNESS_KEYED_DOOR_OPEN.md`.
The prior session had pushed keyed-door coverage through `open west` but left
the `west` traversal unlanded after a live C-oracle probe exposed
`FINDING-026`: Midgaard Captain's Office rendered cityguards before the captain
in ROM, but captain before cityguards in Python.

## Outcomes

### `FINDING-026` — ✅ FIXED

- **Python**: `mud/models/room.py:200`
- **ROM C**: `src/db.c:1747`, `src/handler.c:1557-1559`
- **Gap**: `FINDING-026` — reset-spawned room occupant look order drift.
- **Fix**: `Room.add_mob` now head-inserts into `room.people`, matching ROM
  `char_to_room` for NPC placement. This makes later `M` resets appear first in
  room look order, so Midgaard room `3142` lists the four cityguards before the
  captain.
- **Tests**: added
  `tests/test_spawning.py::test_m_reset_room_people_order_matches_rom_char_to_room`
  (RED `[captain, guard]`, GREEN `[guard, captain]`).

### Keyed-door traversal — ✅ ADDED

- **Python**: `tools/diff_harness/generated.py`
- **ROM C**: `src/act_move.c:200`, `src/handler.c:1557-1559`
- **Change**: `DeterministicNoRngDiffMachine` now has legal `west`/`east`
  traversal rules across Cityguard HQ west door after `open west`.
- **Tests**: focused keyed-door live C replay now includes `west` into
  Captain's Office and `east` back to Cityguard HQ.

## Files Modified

- `mud/models/room.py` — `Room.add_mob` now head-inserts.
- `tests/test_spawning.py` — added reset `M` room-people ordering regression.
- `tools/diff_harness/generated.py` — added keyed-door traversal rules.
- `tests/test_diff_harness_generated.py` — focused keyed-door scenario includes
  `west`/`east`.
- `tools/diff_harness/FINDINGS.md` — marked `FINDING-026` resolved.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — updated Class 11 Phase C note.
- `CHANGELOG.md` — added `2.13.39`.
- `pyproject.toml` — `2.13.38` → `2.13.39`.

## Test Status

- `PYTHONPATH=. pytest -q tests/test_spawning.py::test_m_reset_room_people_order_matches_rom_char_to_room` — 1 passed.
- `PYTHONPATH=. pytest -q tests/test_spawning.py tests/test_diff_harness_generated.py::test_generated_keyed_door_cycle_matches_live_c tests/test_diff_harness_generated.py::test_generated_no_rng_sequences_match_live_c` — 49 passed.
- `PYTHONPATH=. pytest -q tests/test_shops.py tests/test_spec_funs.py tests/integration/test_admin_commands.py` — 82 passed.
- `ruff check .` — clean.
- `PYTHONPATH=. pytest -q` — 5462 passed, 5 skipped.
- `gitnexus_detect_changes(scope="all")` — low risk, no affected execution flows.

## Next Steps

Continue Class 11 / Phase C dynamic differential widening on another
deterministic command/watch-set surface. Good candidates remain `nuke_pets`
lifecycle probing and `TRIG_ENTRY` call-site coverage for mob entry paths; both
should start with ROM C source reads before adding tests.
