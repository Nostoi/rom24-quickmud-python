# Session Status — 2026-06-06 — Diff-Harness Phase C Widening: drink + position (2.13.14)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness Phase C widening — drink container `do_drink` + position
    transitions `rest`/`sleep`/`wake`/`stand`.** The
    `DeterministicNoRngDiffMachine` now covers a bottle of beer (vnum 3001,
    `ITEM_DRINK_CON`) and position transition rules. The drink rule exercises
    the fullness guard path (default test char starts at `condition[FULL]=48`
    >45, so both C and Python block with the same message). Two new live
    C-oracle tests lock both surfaces.
  - **`__cond_full` / `__cond_thirst` meta-commands** added to pyreplay.py
    (Python-only — the C shim does not yet support them).
  - **Prior session bugs fixed and committed**: GIVE-013 (do_give→MobInstance
    crash) and room people list ordering (FINDING-028).
  - **`generated.py` duplicate object definitions** cleaned up.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-06_DRINK_POSITION_WIDEN.md](SESSION_SUMMARY_2026-06-06_DRINK_POSITION_WIDEN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.14 |
| Tests | 84/84 passing (diff harness suite + give + position integration) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 8 static + 10 generated-oracle tests (+2 this session) |
| Generated state machine objects | 6 objects (sword 3021, jacket 3045, bag 3032, torch 3030, bread 3011, bottle beer 3001) + 1 mob (drunk 3064) |
| Generated state machine rules | 29 rules (incl. 4 position transitions, 3 drink rules) |

## Next Intended Task

1. Continue Phase C deterministic diff-harness widening:
   - **Fill/pour containers** — `do_fill` (fountain → drink container) and
     `do_pour` (container → container or out). Needs a fountain room.
   - **Full drink logic** — requires lowering `condition[FULL]` in both C and
     Python drivers so the actual sip-decrement + condition-gain path is
     exercised (currently the fullness guard blocks it).
2. Add RNG-locked combat scenarios only after seed alignment is proven.

## Other open / deferred items

- **FINDING-027 follow-up**: ROM `create_money` clamps invalid input
  (`gold = UMAX(1, gold)`) and never returns NULL; the Python port still returns
  `None` and callers guard on it. Not exercised by any scenario.
- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.
- **C shim `__cond_full` / `__cond_thirst` support** — the Python pyreplay
  supports these meta-commands but the C diffshim needs to be recompiled to
  handle them before the actual drinking logic (sip decrement, condition gains)
  can be exercised in the diff harness.
