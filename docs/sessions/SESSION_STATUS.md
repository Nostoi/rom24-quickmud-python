# Session Status — 2026-06-06 — Diff-Harness Phase C Widening: fill + pour (2.13.15)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness Phase C widening — pour out + fill from fountain.** The
    `DeterministicNoRngDiffMachine` now covers `pour <container> out` (empties a
    drink container) and `fill <container>` (fills from a fountain to max).
    Movement rules to room 3005 (The Sanctuary, south from the temple) and a
    fountain spawn rule (`__oload=3135`) support the fill path. Two new live
    C-oracle tests lock both surfaces.
  - **`generated.py` duplicate object definitions fully cleaned**.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-06_FILL_POUR_WIDEN.md](SESSION_SUMMARY_2026-06-06_FILL_POUR_WIDEN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.15 |
| Tests | 32/32 diff harness suite passing |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 8 static + 12 generated-oracle tests (+2 this session) |
| Generated state machine objects | 7 (6 objects + 1 mob) |
| Generated state machine rules | 34 rules (+5 this session: south/north to 3005, pour out, spawn fountain, fill) |

## Next Intended Task

1. Continue Phase C deterministic diff-harness widening:
   - **Pour between containers** — `pour <source> <target>` (transfer liquid
     between two drink containers). Needs two containers with same liquid type.
   - **Full drink logic** — requires lowering `condition[FULL]` in both C and
     Python drivers so the actual sip-decrement + condition-gain path is
     exercised. Options: recompile C shim with `__cond_full` support, or change
     `make_test_char` defaults in both drivers.
2. Add RNG-locked combat scenarios only after seed alignment is proven.

## Other open / deferred items

- **FINDING-027 follow-up**: ROM `create_money` clamps invalid input
  (`gold = UMAX(1, gold)`) and never returns NULL; the Python port still returns
  `None` and callers guard on it. Not exercised by any scenario.
- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.
- **C shim `__cond_full` / `__cond_thirst` support** — the Python pyreplay
  supports these meta-commands but the C diffshim needs to be recompiled to
  handle them before the actual drinking logic can be exercised.
