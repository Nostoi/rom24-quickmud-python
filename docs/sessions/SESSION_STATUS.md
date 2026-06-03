# Session Status — 2026-06-02 — Flag-hex guard + INV-034 pointer-identity (2.12.77)

## Current State

- **Active mode**: cross-file invariants under the **divergence-class
  completeness lens**. This session swept two Layer-A candidate classes via
  `/rom-divergence-sweep`: class 5 (flag-hex) and class 6 (pointer-identity).
- **Class 5 (flag-hex) → ✅ Layer-A guarded** (`tests/test_flag_hex_convention.py`,
  the 4th static guard). Feasible because a tight prefix-anchored grep had exactly
  one legitimate hit (`wiznet.py`'s `WiznetFlag` enum body — allowlisted). Closed
  4 offenders (2 enum migrations + 2 dead-code deletions, HANDLER-DEAD-001/002).
  No live behavior change. Commits `568639b7`, `6ce23769`.
- **Class 6 (pointer-identity) → reclassified A→C, filed OPEN as INV-034**
  (2.12.77, commit pending). A static guard is infeasible (`==`/`!=` not
  type-discriminable by grep). The probe *discovered* the root cause is live:
  `Character`/`Object` are value-eq `@dataclass`es and the spawn path leaves
  `instance_id`/`id` unset, so distinct same-proto entities compare `==`-equal
  (empirically verified) — poisoning ~91 `in`/`remove` sites. Recall oracle =
  INV-031(c) (already fixed `is_same_group`→`is`). Filed INV-034 (Layer C, ⚠️
  OPEN) + strict-xfail demo test + **new AGENTS.md "Entity identity" parity rule**
  ("use `is`, not `==`"). **Root fix deferred** (~91-site blast radius; needs a
  value-eq test-reliance sweep) — probe-only mandate honored.
- **Layer A is now at its feasible ceiling**: 4/4 classes that admit a static
  chokepoint-guard have one (RNG, equipment-key, attribute-naming, flag-hex); the
  two that don't (async-delivery, pointer-identity) are behavioral Layer C.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_FLAG_HEX_LAYER_A_GUARD.md](SESSION_SUMMARY_2026-06-02_FLAG_HEX_LAYER_A_GUARD.md)
  (flag-hex + the class-6/INV-034 addendum).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.77 |
| Tests | 5356 passed, 4 skipped (flag-hex full run) + 2 new xfailed (INV-034 demo) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 27 rows (INV-034 added, ⚠️ OPEN) |
| Divergence-class lens | **Layer A at feasible ceiling** (4/4 guarded); class 6 reclassified A→C (INV-034 OPEN) |
| Lint | `ruff check .` 1762 pre-existing errors (none introduced; edited lines clean) |

## Next Intended Task

1. **Root-fix INV-034 (scoped session — the highest-value concrete next step).**
   Convert `Character`/`Object` to identity equality (`@dataclass(eq=False)`,
   restoring identity `==` + identity `__hash__`). **Gate first** on
   `grep -rn "assert .*(obj|char|victim|item).*==" tests/` to find/repair any test
   relying on value-equality, then run the full suite. Flips the strict-xfail
   `test_inv034_pointer_identity_divergence.py` to xpass and promotes class 6 to ✅.
2. **Highest-ceiling (deliberate multi-day project):** `diff_harness` Hypothesis
   widening (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
3. **Standing cross-INV candidate:** mob-trigger ordering (bribe/exit/fight/kill/
   hpcnt); INV tracker consolidation (now 27 rows, past the ~20 soft cap).

> **Push note:** 2.12.76 (`568639b7`, `6ce23769`) + 2.12.77 (this INV-034 work,
> commit pending) + handoff are on local `master`, **not pushed** — on top of the
> unpushed 2.12.72–2.12.75 from prior sessions. CHANGELOG/version reflect 2.12.77.
