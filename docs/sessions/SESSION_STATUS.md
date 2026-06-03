# Session Status — 2026-06-03 — diff-harness Hypothesis Phase C object lifecycle (2.13.0)

## Current State

This session started **Phase C** of `diff_harness` Hypothesis widening by adding
deterministic object lifecycle coverage on top of the Phase A/B live C oracle
and generated no-RNG state machine.

- **Phase A complete:** `tools/diff_harness/oracle.py` provides live C traces
  for arbitrary in-memory scenarios.
- **Phase B complete:** `tools/diff_harness/pyreplay.py` provides the shared
  Python replay driver, and `tools/diff_harness/generated.py` provides the
  bounded no-RNG generated state machine.
- **Phase C started:** generated coverage now supports `__oload=<vnum>` object
  injection and legal get/wield/wear/remove/drop rules for a small sword and
  scale mail jacket.
- **FINDING-016 fixed:** generated coverage found remove→rewear failed because
  `_remove_obj` left stale `obj.worn_by`; `mud/commands/obj_manipulation.py`
  now clears it after `unequip_char`.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_DIFF_HARNESS_HYPOTHESIS_PHASE_C_OBJECTS.md](SESSION_SUMMARY_2026-06-03_DIFF_HARNESS_HYPOTHESIS_PHASE_C_OBJECTS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.0 |
| Tests | Focused generated diff-harness + remove regression slice `python3 -m pytest -n0 tests/test_diff_harness_unit.py tests/test_diff_harness_generated.py tests/test_differential_smoke.py tests/integration/test_remove_command.py::test_do_remove_happy_path_emits_both_messages -q` → 20 passed |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 31 active rows |
| Open engine bugs | **None** known. |

## Next Intended Task

Continue `diff_harness` Hypothesis widening with **Phase C — widen coverage**:

1. Add more deterministic legal command rules and watch-set fields where useful
   (good next targets: container put/get with `__oload` bag/box, light hold and
   room-light snapshots, bounded money/shop paths if setup stays deterministic).
2. Keep generated examples bounded; this test runs two engines per example.
3. Add RNG-locked combat only after proving seed alignment per step.
4. File every real mismatch in `tools/diff_harness/FINDINGS.md`; never overwrite
   a golden to hide a divergence.

## Other open / deferred items

- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate or it's reworked to changed-files-only.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact (`SimpleNamespace` stub lacks `exit_info`); not an engine bug.
