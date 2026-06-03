# Session Summary — 2026-06-03 — diff-harness Hypothesis Phase C object lifecycle

## Scope

Continued the `diff_harness` Hypothesis widening project from the Phase B
generated no-RNG state machine. This session started **Phase C** by widening the
generated command vocabulary from movement/look/inventory into deterministic
object lifecycle paths, then fixed the first real divergence it surfaced.

## Outcome

- Added `__oload=<vnum>` support to both live C and Python replay:
  - **C shim**: `src/diff_shim/diffmain.c` uses ROM `create_object` +
    `obj_to_room`.
  - **Python replay**: `tools/diff_harness/pyreplay.py` uses `spawn_object` +
    `Room.add_object`.
- Widened `DeterministicNoRngDiffMachine` to generate legal object transitions
  for a small sword (`3021`) and scale mail jacket (`3045`):
  `__oload`, `get`, `wield`/`wear`, `remove`, and `drop`.
- Removed the previous non-takeable donation-pit get/drop model from the
  generated machine; ROM and Python both rejected it, so it was not a legal
  lifecycle path.
- Tightened the C snapshot `inventory` field to carried, non-equipped objects.
  Equipment remains compared through the existing `equipment` field.
- Added deterministic live C/Python coverage for the object lifecycle path.

## FINDING-016 — ✅ FIXED

- **Python**: `mud/commands/obj_manipulation.py::_remove_obj`
- **ROM C**: `src/handler.c:1804-1877` (`unequip_char`) +
  `src/act_obj.c:1387-1391` (`remove_obj`)
- **Symptom**: generated sequence
  `__oload=3045; get jacket; wear jacket; remove jacket; wear jacket`
  converged until the second `wear jacket`; ROM wore the jacket again, Python
  returned `"You are already wearing that."`
- **Root cause**: `_remove_obj` reset `wear_loc` and equipment membership but
  left the Python-only `obj.worn_by` pointer set to the character. `do_wear`
  rejected that stale pointer as already equipped.
- **Fix**: `_remove_obj` now clears `obj.worn_by = None` after `unequip_char`;
  the equipment removal loop also uses identity comparison (`is`) per ROM
  pointer semantics.
- **Tests**: `tests/integration/test_remove_command.py` now asserts
  remove clears `worn_by` and permits immediate re-wear.

## Files Modified

- `tools/diff_harness/generated.py` — object lifecycle rules for generated
  no-RNG scenarios.
- `tools/diff_harness/pyreplay.py` — Python `__oload` replay support.
- `src/diff_shim/diffmain.c` — C `__oload` support and carried-only inventory
  snapshot semantics.
- `tools/diff_harness/schema.py` — snapshot inventory definition clarified.
- `tests/test_diff_harness_generated.py` — live generated and deterministic
  object lifecycle tests.
- `tests/test_diff_harness_unit.py` — Python replay `__oload` unit coverage.
- `mud/commands/obj_manipulation.py` — FINDING-016 fix.
- `tests/integration/test_remove_command.py` — FINDING-016 regression.
- `tools/diff_harness/FINDINGS.md` — filed FINDING-016 as resolved.
- `docs/parity/ACT_OBJ_C_AUDIT.md` — `do_remove`/`remove_obj` note refreshed.
- `tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md` and
  `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — Phase C status updated.
- `CHANGELOG.md` — Phase C + FINDING-016 entries.
- `pyproject.toml` — `2.12.99` → `2.13.0`.

## Verification

- `python3 -m pytest -n0 tests/test_diff_harness_generated.py -q` → 2 passed.
- `python3 -m pytest -n0 tests/test_diff_harness_unit.py tests/test_diff_harness_generated.py tests/test_differential_smoke.py tests/integration/test_remove_command.py::test_do_remove_happy_path_emits_both_messages -q`
  → 20 passed.

## Next Steps

Continue Phase C with more deterministic command/watch-set widening. Good next
targets are container operations (`put/get` with `__oload` bag/box), light hold
and room-light snapshots, and deterministic shop or money paths if the setup can
stay bounded. Add RNG-locked combat only after proving seed alignment per step.
