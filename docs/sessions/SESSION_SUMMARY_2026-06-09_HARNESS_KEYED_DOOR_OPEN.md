# Session Summary — 2026-06-09 — harness keyed-door open

## Scope

Continued from `SESSION_SUMMARY_2026-06-09_HARNESS_KEYED_DOOR_RULES.md`.
The active work remained Class 11 / Phase C dynamic differential widening in
`tools/diff_harness/generated.py`. This pass extended the newly added keyed-door
fixture one step further by adding the deterministic `open` leg.

## Outcomes

### Keyed-door `open west` generated rule — ✅ ADDED

- **Python**: `tools/diff_harness/generated.py`
- **ROM C**: `src/act_move.c:345-455` (`do_open`)
- **Harness fixture**: Midgaard Cityguard HQ room `3110`, west door to room
  `3142`, iron key object `3120`.
- **Change**: Added `open_hq_west_door` after the generated close/lock/unlock/pick
  state cycle. The focused live C-oracle replay now continues through `open west`
  after the pick-lock branch.
- **Tests**: `tests/test_diff_harness_generated.py::test_generated_keyed_door_cycle_matches_live_c`
  and `::test_generated_no_rng_sequences_match_live_c` passed.

### `FINDING-026` occupant look-order drift — 🔄 FILED

- **Finding**: `tools/diff_harness/FINDINGS.md`
- **Surfaced by**: a traversal probe after `open west`.
- **Observed**: ROM room look for Captain's Office lists four cityguards before
  the captain; Python lists the captain before the cityguards.
- **Outcome**: Traversal rules (`west` / `east`) were not landed in the generated
  machine. The divergence is filed durably for a scoped reset/`char_to_room`
  occupant-order pass.

## Files Modified

- `tools/diff_harness/generated.py` — added `open_hq_west_door`.
- `tests/test_diff_harness_generated.py` — focused keyed-door replay now includes
  `open west`.
- `tools/diff_harness/FINDINGS.md` — added `FINDING-026`.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded keyed-door open widening
  and the traversal blocker.
- `CHANGELOG.md` — added `[2.13.38]`.
- `pyproject.toml` — `2.13.37` → `2.13.38`.

## Test Status

- `PYTHONPATH=. pytest -q tests/test_diff_harness_generated.py::test_generated_keyed_door_cycle_matches_live_c` — 1 passed.
- `PYTHONPATH=. pytest -q tests/test_diff_harness_generated.py::test_generated_no_rng_sequences_match_live_c` — 1 passed.
- `ruff check .` — clean.
- `PYTHONPATH=. pytest -q` — 5461 passed, 5 skipped.

## Next Steps

Either scope `FINDING-026` (ROM `char_to_room` / reset occupant insertion order
vs Python reset/mob placement order) or continue Class 11 widening on a
different deterministic command surface that does not depend on room occupant
ordering. The prior non-harness candidates also remain: `nuke_pets` lifecycle
probing and `TRIG_ENTRY` call-site coverage for mob entry paths.
