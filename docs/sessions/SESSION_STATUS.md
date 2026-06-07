# Session Status — 2026-06-06 — Diff-Harness Phase C Widening: Pour Between Containers (2.13.16)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness Phase C widening — pour between containers.** The
    `DeterministicNoRngDiffMachine` now covers `pour <source> <target>` (transfer
    liquid between two drink containers). Added coffee cup object (vnum 3101,
    capacity 6) with load/get/pour-out/pour-between rules. The live C-oracle
    test exercises the full `do_pour` transfer path (ROM `act_obj.c:1100-1135`):
    liquid type guard (skipped for empty target), amount transfer (min(16, 6) =
    6 sips), and liquid type copy from source to target.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-06_POUR_BETWEEN_WIDEN.md](SESSION_SUMMARY_2026-06-06_POUR_BETWEEN_WIDEN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.16 |
| Tests | 33/33 diff harness suite passing |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 8 static + 13 generated-oracle tests (+1 this session) |
| Generated state machine objects | 8 (7 objects + 1 mob) |
| Generated state machine rules | 38 rules (+4 this session: load/get/pour-out/pour-between coffee cup) |

## Next Intended Task

1. Continue Phase C deterministic diff-harness widening:
   - **Full drink logic** — requires adding `__cond_full=0` / `__cond_thirst=0`
     meta-command handlers to the C shim (`src/diff_shim/diffmain.c`, ~5 lines
     each after the `__silver=` handler), then rebuilding the binary. The Python
     side (`tools/diff_harness/pyreplay.py`) already handles both. Once the C
     shim is rebuilt, the `drink_bottle_beer` rule in `generated.py` can insert
     `__cond_full=0` before `drink bottle` to exercise actual drinking logic
     (sip decrement, condition gains, liquid effects).
   - **Pour into held container** — `pour <source> <target_character>` where the
     target character holds a drink container. Exercises the `vch` branch of
     `do_pour` (ROM `act_obj.c:1146-1157`), which needs a mob in the room
     already holding a drink container.

## Other open / deferred items

- **FINDING-027 follow-up**: ROM `create_money` clamps invalid input
  (`gold = UMAX(1, gold)`) and never returns NULL; the Python port still returns
  `None` and callers guard on it. Not exercised by any scenario.
- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.
