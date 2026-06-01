# Session Status — 2026-06-01 — INV-025 clone ACT trigger dispatch (2.12.21)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.21)**:
  - **INV-025 clone sweep — COMPLETED**. `mud/commands/imm_search.py:do_clone`
    now dispatches `TRIG_ACT` for the ROM `act(TO_ROOM)` lines on both clone
    branches.
  - ROM sources verified: `src/act_wiz.c:2405` (`clone object` TO_ROOM),
    `:2449` (`clone mobile` TO_ROOM), and `src/comm.c:2384`
    (`MOBtrigger`-gated `mp_act_trigger` dispatch).
  - Object clone dispatch threads the cloned object as `arg1` (`$p`); mobile
    clone dispatch threads the cloned mobile as `arg2` (`$N`). The mobile branch
    preserves ROM's recipient set: the cloned NPC is in the room before the
    TO_ROOM act line is emitted.
  - Enforcement tests: `tests/integration/test_inv025_clone_act_trigger_dispatch.py`
    (2 passed).
  - Adjacent regression sweep: existing clone broadcast and act_wiz clone command
    tests (8 passed total across targeted commands).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_INV025_CLONE_ACT_TRIGGER.md](SESSION_SUMMARY_2026-06-01_INV025_CLONE_ACT_TRIGGER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.21 |
| Targeted tests | `test_inv025_clone_act_trigger_dispatch.py`: 2 passed; adjacent clone sweep: 8 passed |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced |
| Open correctness gaps | None currently filed; INV-025 sweep continues. |
| Active focus | INV-025 cross-file-invariant sweep (remaining non-combat ROM `act()` narrations) |

## Next Intended Task

Continue the broader **INV-025** sweep for remaining non-combat narrations whose
matching ROM sites use `act()` and Python currently only calls `broadcast_room`
or another delivery primitive without `mp_act_trigger`.

Likely next target:

1. Re-scan remaining `src/act_wiz.c` `act()` sites not covered by the current
   INV-025 tests, after checking each ROM source site before wiring anything.
2. Skip descriptor-iteration `send_to_char` paths such as `do_echo`, `do_recho`,
   `do_zecho`, and `do_pecho` unless a fresh ROM source check proves otherwise.
