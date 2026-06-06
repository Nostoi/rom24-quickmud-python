# Session Summary — 2026-06-06 — Diff-Harness Phase C Widening: fill + pour (2.13.15)

## Scope

Picked up from SESSION_STATUS "Next Intended Task — Fill/pour containers."
Added `pour <container> out` (empties drink container) and `fill <container>`
(fills from fountain to max) to the `DeterministicNoRngDiffMachine`.

## Outcomes

### Widening: pour out

- **`_ObjectState` extended**: added `poured_out: bool` field for tracking
  emptied containers.
- **`pour_out_bottle` rule**: pours out the bottle beer (vnum 3001, 16 sips
  of beer). ROM `do_pour` → `_pour_out` sets `value[1]=0` (emptied) and
  `value[3]=0` (cleared poison flag). Deterministic — no RNG.
- **C-oracle test**: `test_generated_pour_out_matches_live_c` — verify
  pour-out output messages match between C and Python.

### Widening: fill from fountain

- **Room 3005 (The Sanctuary)**: discovered via area data — room 3001 has a
  **south** exit (D2 → 3005), not down as originally assumed. Return is north
  (D0 from 3005 → 3001).
- **Movement rules**: `south_to_sanctuary` (3001 → 3005) and `north_to_temple`
  (3005 → 3001), both gated on `Position.STANDING`.
- **`spawn_fountain` rule**: `__oload=3135` (fountain object) in room 3005,
  tracked via `self._fountain_room`. Ensures `do_fill` can find the fountain.
- **`fill_bottle` rule**: fills the empty bottle from the fountain with water
  (liquid type 0). ROM fill always fills to max (16 sips). Resets `drank` and
  `poured_out` flags.
- **C-oracle test**: `test_generated_fill_from_fountain_matches_live_c` —
  pour out → south → oload fountain → fill → north.

### Bug: duplicate object definitions fully cleaned

- The earlier session's duplicate cleanup didn't fully remove all silently-
  overwriting `_ObjectState` assignments. Lines 90-115 (scale_jacket, torch,
  bread, bag duplicates) are now fully removed.

### Files Modified

- `tools/diff_harness/generated.py` — `poured_out` field, `_fountain_room`
  tracker, 5 new rules (south_to_sanctuary, north_to_temple, pour_out_bottle,
  spawn_fountain, fill_bottle), `watch_rooms` extended to [3001, 3005, 3054].
- `tests/test_diff_harness_generated.py` — 2 new C-oracle tests.
- `CHANGELOG.md` — 2.13.15 section.
- `pyproject.toml` — 2.13.14 → 2.13.15.
- `docs/sessions/SESSION_STATUS.md` — updated.

## Test Status

- Diff harness: **32/32 passing** (7 smoke + 13 unit + 12 generated, +2 new).
- `ruff check .` clean, `ruff format --check .` clean.

## Next Steps

1. Continue Phase C widening:
   - **Pour between containers** — `pour <source> <target>` (transfer liquid
     between two drink containers). Needs two containers with same liquid type
     (or compatible).
   - **Full drink logic** — requires lowering `condition[FULL]` in both drivers.
2. Add RNG-locked combat scenarios only after seed alignment is proven.
