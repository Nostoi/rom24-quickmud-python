# Session Status — 2026-06-08 — INV-025 object update act triggers (2.13.36)

## Current State

- **Active mode**: cross-file invariants / INV-025 ad-hoc follow-up sweep
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Object decay / object-affect wear-off TRIG_ACT follow-up closed.**
    `mud/game_loop.py` now dispatches `mp_act_trigger` for object decay
    `act(message, rch, obj, TO_ROOM/TO_CHAR)` and object-affect `msg_obj`
    `act(..., TO_ALL)` paths, mirroring ROM `src/update.c:937-951` and
    `src/update.c:1014-1022`.
  - Carried object-affect `msg_obj` wear-off now mirrors ROM's TO_CHAR-only
    branch (no non-ROM room broadcast / room TRIG_ACT), and object-update
    TO_CHAR act lines are capitalized before delivery.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_INV025_OBJECT_UPDATE_ACT_TRIGGERS.md](SESSION_SUMMARY_2026-06-08_INV025_OBJECT_UPDATE_ACT_TRIGGERS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.36 |
| Tests | 5458 passing, 5 skipped (5463 collected) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 17 generated-oracle tests |
| INV-025 object-update follow-up | Closed (3 new regressions) |

## Next Intended Task

**Remaining cross-file invariant candidates:**

1. **Hypothesis state machine widening** (Class 11 Phase C, ongoing): add
   `give` / `lock` / `unlock` / `pick` command rules to
   `DeterministicNoRngDiffMachine` in `tools/diff_harness/generated.py`.
2. **`nuke_pets` lifecycle**: probe whether Python correctly extracts charmed
   followers on their master's death/extract (`src/handler.c:nuke_pets`).
3. **`TRIG_ENTRY` call-site coverage**: verify `mp_greet_trigger` fires when a
   mob enters a room — currently wired in `mud/world/movement.py` but not
   confirmed against all entry paths.
