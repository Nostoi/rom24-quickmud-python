# Session Summary — 2026-06-09 — harness keyed-door rules

## Scope

Continued from `SESSION_SUMMARY_2026-06-08_INV025_OBJECT_UPDATE_ACT_TRIGGERS.md`.
The next queued cross-file task was Class 11 / Phase C Hypothesis state-machine
widening in `tools/diff_harness/generated.py`, specifically adding deterministic
door-command coverage after the existing object, shop, drink, pour, give, and
affect-expiry generated rules.

## Outcomes

### `DeterministicNoRngDiffMachine` keyed-door rules — ✅ ADDED

- **Python**: `tools/diff_harness/generated.py`
- **ROM C**: `src/act_move.c:571-705`, `src/act_move.c:706-840`,
  `src/act_move.c:841-994`
- **Harness fixture**: Midgaard Cityguard HQ room `3110`, west door to room
  `3142`, iron key object `3120`.
- **Change**: Added generated rules for `close west`, `lock west`, `unlock west`,
  and `pick west`. The pick rule teaches `pick lock`, seeds the RNG, and raises
  the generated PC to level 30 via harness meta-command so ROM `get_skill`
  returns the learned skill for the default class.
- **Tests**: `tests/test_diff_harness_generated.py::test_generated_no_rng_sequences_match_live_c`
  and `::test_generated_keyed_door_cycle_matches_live_c` passed.

### Diff-harness meta-commands — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c`
- **Python replay**: `tools/diff_harness/pyreplay.py`
- **Change**: Added `__goto=<vnum>` to move the test character silently to a
  stock fixture room, and `__level=<n>` to satisfy ROM class-level skill gates
  without changing the generated machine's default level globally.
- **Tests**: `tests/test_diff_harness_unit.py` now covers both Python replay
  meta-commands.

## Files Modified

- `tools/diff_harness/generated.py` — keyed-door state and generated rules.
- `tools/diff_harness/pyreplay.py` — Python replay `__goto` / `__level`.
- `src/diff_shim/diffmain.c` — C oracle `__goto` / `__level`.
- `tests/test_diff_harness_generated.py` — focused live C keyed-door replay.
- `tests/test_diff_harness_unit.py` — Python replay meta-command regressions.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded Class 11 Phase C widening.
- `CHANGELOG.md` — added `[2.13.37]`.
- `pyproject.toml` — `2.13.36` → `2.13.37`.

## Test Status

- `PYTHONPATH=. pytest -q tests/test_diff_harness_unit.py` — 15 passed.
- `PYTHONPATH=. pytest -q tests/test_diff_harness_generated.py::test_generated_no_rng_sequences_match_live_c tests/test_diff_harness_generated.py::test_generated_keyed_door_cycle_matches_live_c` — 2 passed.
- `ruff check .` — clean.
- `PYTHONPATH=. pytest -q` — 5461 passed, 5 skipped.

## Next Steps

Continue Class 11 dynamic widening with another deterministic command surface.
Good next candidates remain `nuke_pets` lifecycle probing (`src/handler.c`) and
`TRIG_ENTRY` call-site coverage for mobs entering rooms, both listed in the prior
`SESSION_STATUS.md`. RNG-locked combat should still wait until seed alignment is
proven.
