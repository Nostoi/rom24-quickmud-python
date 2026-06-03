# Session Summary — 2026-06-03 — diff-harness live C oracle (Phase A)

## Scope

Picked up from `SESSION_STATUS.md`'s top next-task candidate: `diff_harness`
Hypothesis widening, the enumeration-independent path for unknown ROM parity
divergences. This session completed **Phase A** from
`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`: reusable live C oracle
infrastructure. No gameplay code changed.

## Outcome

- Added `tools/diff_harness/oracle.py`.
- New API:
  - `build_c_input(sc)` builds the `src/diffshim` stdin protocol for any
    in-memory `Scenario`.
  - `drive_c_oracle(sc, binary)` runs the C shim live and returns `StepSnap`
    traces without reading or writing committed goldens.
- `tools/diff_harness/capture.py` now delegates to the same live-oracle path,
  so existing golden capture and future generated scenarios share one C driver.
- Added unit coverage for stdin construction, live-event parsing into
  `StepSnap`, and C binary failure surfacing.
- Updated the Hypothesis-widening proposal and divergence-class roster to mark
  Phase A complete and point the next session at Phase B.
- Version: `2.12.97 → 2.12.98`.

## Files Modified

- `tools/diff_harness/oracle.py` — new reusable live C oracle.
- `tools/diff_harness/capture.py` — delegates golden trace capture to
  `drive_c_oracle`.
- `tests/test_diff_harness_unit.py` — 3 new oracle tests.
- `tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md` — Phase A marked
  complete.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — Class 11 dynamic-widening note
  updated.
- `CHANGELOG.md` — Added entry for Phase A.
- `pyproject.toml` — version bump to 2.12.98.

## Verification

- `python3 -m pytest -n0 tests/test_diff_harness_unit.py -q` → 11 passed.
- `python3 -m pytest -n0 tests/test_differential_smoke.py tests/test_diff_harness_unit.py -q`
  → 15 passed.
- `python3 -m tools.diff_harness.capture --check` → all four committed
  scenarios ok (`affect_armor`, `combat_melee_rounds`, `movement_get_drop`,
  `spell_combat`).

## Next Steps

1. **Phase B — no-RNG Hypothesis state machine.** Add the dev/test dependency
   if needed, generate legal deterministic command sequences (`look`,
   movement, get/drop, wear/remove, inventory), drive C via `drive_c_oracle`,
   drive Python via the existing replay path, and diff/shrink failures.
2. Keep any mismatch as a `tools/diff_harness/FINDINGS.md` finding, not a
   golden overwrite.

## Outstanding

- Phase B and C remain open; Phase A is complete.
- No new engine bugs surfaced.
