# Session Status — 2026-06-03 — INV-035 mobile mobprog default-position gate (2.12.83)

## Current State

- **Active mode**: cross-file invariants via **probe-then-scope** under the
  divergence-class completeness lens.
- **INV-035 (mobile mobprog default-position gate) → ✅ ENFORCED (2.12.83).**
  ROM `src/update.c:443-465 mobile_update` runs `TRIG_DELAY` then `TRIG_RANDOM`
  only while a mob is still at its prototype default position; a firing trigger
  skips standing-only AI, and non-standing mobs stop before scavenging/wandering.
  Python `mud/ai/__init__.py:mobile_update` already matched this ordering. Added
  a durable guard at
  `tests/test_game_loop.py::test_mobile_update_mobprog_default_position_gate_precedes_standing_ai`.
- **No production divergence surfaced** in this probe. This session added a test
  and tracker row only, plus changelog/version/session docs.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_INV035_MOBILE_MPROG_GATE.md](SESSION_SUMMARY_2026-06-03_INV035_MOBILE_MPROG_GATE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.83 |
| Tests | `pytest -n0 tests/test_game_loop.py -q` → 20 passed |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 28 active rows (INV-035 ✅ ENFORCED) |
| Divergence-class lens | Layer A 4/4 feasible; class 6 (pointer-identity) ✅ FULLY CLOSED |
| Lint / impact | `ruff check tests/test_game_loop.py` clean; repo-wide `ruff check .` still fails on pre-existing lint outside scope; GitNexus detect_changes LOW risk, 0 affected processes |

## Next Intended Task

Candidate next passes:

1. **Highest-ceiling (multi-day):** `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
2. **New cross-INV probe area** — position-transition edges or affect ticks.
3. **Housekeeping:** INV tracker consolidation (28 active rows, past the ~20
   soft cap).
