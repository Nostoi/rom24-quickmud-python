# Session Summary — 2026-06-03 — diff-harness Hypothesis widening Phase B

## Scope

Continued the `diff_harness` Hypothesis widening project from the Phase A live C
oracle handoff. This session completed **Phase B**: a bounded no-RNG generated
state machine that drives live ROM C and Python through legal deterministic
command sequences and diffs the resulting traces. No gameplay code changed.

## Outcome

- Added `tools/diff_harness/pyreplay.py`, extracting the Python replay setup and
  command loop from `tests/test_differential_smoke.py`.
- `tests/test_differential_smoke.py` now delegates to `drive_python_replay(sc)`.
- Added `tools/diff_harness/generated.py` with
  `DeterministicNoRngDiffMachine`, a Hypothesis `RuleBasedStateMachine` over:
  `look`, `inventory`, north/south movement, and legal `get pit` / `drop pit`.
- Added `tests/test_diff_harness_generated.py`, which runs the generated no-RNG
  slice against live `src/diffshim` when the binary exists.
- Declared `hypothesis>=6.100` in the `dev` and `test` extras.
- Added `.hypothesis/` to `.gitignore` for the local Hypothesis example/cache
  directory.
- Updated `tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md` and
  `docs/parity/DIVERGENCE_CLASS_ROSTER.md` to mark Phases A/B complete.
- Version: `2.12.98 → 2.12.99`.

## Files Modified

- `tools/diff_harness/pyreplay.py` — new reusable Python-side replay driver.
- `tools/diff_harness/generated.py` — new bounded no-RNG generated state
  machine.
- `tests/test_diff_harness_generated.py` — live C/Python generated comparison.
- `tests/test_diff_harness_unit.py` — `drive_python_replay` unit coverage.
- `tests/test_differential_smoke.py` — delegates to `drive_python_replay`.
- `pyproject.toml` — `hypothesis` dev/test dependency + version bump.
- `.gitignore` — ignore Hypothesis local cache.
- `CHANGELOG.md` — updated Phase A/B entry.
- `tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md` — Phase B complete.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — Class 11 status updated.
- `docs/sessions/SESSION_STATUS.md` — canonical pointer updated.

## Verification

- `python3 -m pytest -n0 tests/test_diff_harness_unit.py tests/test_differential_smoke.py tests/test_diff_harness_generated.py -q`
  → 17 passed.
- No generated mismatch surfaced in the bounded Phase B slice.

## Next Steps

1. **Phase C — widen generated differential coverage.** Add more deterministic
   legal commands and widen the watch-set where useful.
2. Add RNG-locked combat only after proving seed alignment per step.
3. Keep every mismatch as a `tools/diff_harness/FINDINGS.md` finding; never
   overwrite goldens to hide divergence.

## Outstanding

- Phase C remains open.
- No new engine bugs surfaced.
