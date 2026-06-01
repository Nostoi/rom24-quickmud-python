# Session Status — 2026-06-01 — MOVE-004 movement PERS masking (2.12.27)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.27)**:
  - **MOVE-004 — COMPLETED**.
    - `mud/world/movement.py:move_character`: directional movement
      departure/arrival room lines now render per recipient via `act_format`
      before delivery and before `TRIG_ACT`, matching ROM
      `src/act_move.c:197,202` + `src/comm.c:2230-2385`.
    - `docs/parity/ACT_MOVE_C_AUDIT.md`: filed and closed stale-audit
      correction as MOVE-004.
    - `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`: INV-025 movement note
      refreshed to record the per-recipient PERS correction.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_MOVE004_PERS_MASKING.md](SESSION_SUMMARY_2026-06-01_MOVE004_PERS_MASKING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.27 |
| Targeted tests | MOVE-004 movement + prior ENTER-017/MOBPROG-008 targeted checks: 12 passed; movement neighborhood: 21 passed |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | TRAIN-005 remains open in `ACT_MOVE_C_AUDIT.md`; no new open gap from this probe |

## Next Intended Task

Continue the cross-file invariant probe pass:
1. Review whether portal movement room broadcasts need the same per-recipient
   PERS treatment as MOVE-004, then file a stable ENTER gap if a failing test
   confirms divergence.
2. If the movement/mobprog surface is exhausted, pick a standing candidate:
   affect ticks, position transitions, or group/follower chain.
3. Optional hygiene: clean pre-existing Ruff issues in
   `tests/integration/test_act_enter_gaps.py` if targeted lint over that whole
   file is needed.
