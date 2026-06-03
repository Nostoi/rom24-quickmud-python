# Session Status — 2026-06-02 — INV-034 pointer-identity root fix (2.12.78)

## Current State

- **Active mode**: cross-file invariants under the **divergence-class
  completeness lens**. This session executed the prior session's documented
  next task: the **root fix of INV-034** (pointer-identity, divergence class 6).
- **INV-034 (pointer-identity) → ✅ ENFORCED, class 6 → ✅ FIXED** (2.12.78,
  commit `199827b4`). `Character` and `Object` are now `@dataclass(eq=False)`,
  so `__eq__`/`__hash__` are inherited from `object` (identity compare + identity
  hash = ROM pointer semantics; entities also become hashable). The pre-flight
  gating sweep (`grep "assert .*(obj|char|victim|item).*==" tests/`) confirmed no
  test relied on distinct-twin value-equality. The two strict-xfail demos in
  `tests/test_inv034_pointer_identity_divergence.py` flipped xfail→pass and were
  converted to plain assertions. Production `attacker != victim` / decay-loop
  `object_registry.remove` sites are *corrected*, not regressed.
- **Layer A remains at its feasible ceiling** (4/4 static-guardable classes:
  RNG, equipment-key, attribute-naming, flag-hex). The two behavioral classes
  (async-delivery class 4, pointer-identity class 6) are Layer C — and class 6 is
  now enforced via the model-level fix rather than a per-site grep.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INV034_POINTER_IDENTITY_ROOT_FIX.md](SESSION_SUMMARY_2026-06-02_INV034_POINTER_IDENTITY_ROOT_FIX.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.78 |
| Tests | 5358 passed, 4 skipped (full run) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 27 rows (INV-034 now ✅ ENFORCED) |
| Divergence-class lens | Layer A 4/4 feasible; **class 6 (pointer-identity) ✅ FIXED** (Character/Object eq=False; Room follow-up open) |
| Lint | `ruff check` clean on edited files (repo carries 1762 pre-existing errors; none introduced) |

## Next Intended Task

1. **`Room` identity equality (small follow-up — fully closes class 6).** Same
   class as INV-034, lower risk (vnum-keyed singletons; world-load/area tests may
   compare rooms by value). Write a Room identity test mirroring `test_inv034_*`,
   see it fail, flip `mud/models/room.py:Room` → `@dataclass(eq=False)` in its
   own commit, gated on a `Room == Room` test-reliance sweep.
2. **Highest-ceiling (deliberate multi-day project):** `diff_harness` Hypothesis
   widening (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
3. **Standing cross-INV candidate:** mob-trigger ordering (bribe/exit/fight/kill/
   hpcnt); INV tracker consolidation (now 27 rows, past the ~20 soft cap).

> **Push note:** 2.12.78 (`199827b4`) is on local `master`, **not pushed** — on
> top of the unpushed 2.12.72–2.12.77 from prior sessions. CHANGELOG/version
> reflect 2.12.78.
