# Session Status — 2026-06-10 — drink/eat condition lifecycle scenario (2.13.66)

## Current State

- **Active mode**: cross-file invariants pass + diff-harness coverage expansion
- **Last completed**:
  - **`drink_eat_condition_lifecycle` scenario** — 27th diff-harness scenario,
    exercising `do_drink` (fountain) and `do_eat` (bread) with ROM condition
    threshold messages. C golden captured; Python matches.
  - **`do_eat` pcdata condition fix** — `consumption.py:do_eat` was reading
    condition from a shadow `char.condition` attribute; fixed to read from
    `ch.pcdata.condition` consistently with `do_drink` (ROM `ch->pcdata->condition`).
  - **`pyreplay.py` condition meta-commands fixed** — `__cond_full=`,
    `__cond_thirst=`, `__cond_hunger=` now correctly write to `char.pcdata.condition`
    (were silent no-ops for `do_drink` behavior before).
  - **`__cond_hunger=` meta-command added** to both `diffmain.c` and `pyreplay.py`.
  - 5508 tests pass, 4 skipped; diff-harness 27 scenarios, 46 C-oracle tests.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_DRINK_EAT_CONDITION_LIFECYCLE.md](SESSION_SUMMARY_2026-06-10_DRINK_EAT_CONDITION_LIFECYCLE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.66 |
| Tests | 5508 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 27 scenarios, 46 C-oracle tests passing, 0 skipped, 0 xfailed |
| FINDINGS.md highest ID | FINDING-033 (✅ RESOLVED — all findings resolved) |

## Next Intended Task

Cross-file invariants remains the active pass. All known open findings are resolved.
Concrete candidates:

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **`gain_condition` audit** — Python `do_eat` uses inline `min(48, ...)` arithmetic
   instead of calling `gain_condition`. The C golden confirmed output matches, but a
   direct audit of `gain_condition` in `mud/utils/update.py` against
   `src/update.c:367` would close remaining parity questions on tick-based
   condition decay (hunger/thirst decrement each tick).

3. **Further diff-harness coverage** — condition decay over `__char_update` ticks,
   poison-food lifecycle, or `do_buy`/`do_sell` shop condition paths.
