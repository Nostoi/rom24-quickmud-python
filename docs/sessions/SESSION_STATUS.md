# Session Status — 2026-04-30 — `act_wiz.c` stat family parity review (WIZ-039..044)

## Current State

- **Active audit**: `act_wiz.c` ↔ `mud/commands/imm_search.py` (stat family review — 6 residual gaps closed)
- **Last completed**: WIZ-039..044 (`do_mstat` practices/hitroll/damroll/age/carry-weight fixes; `do_ostat` number/weight helpers; `do_rstat` objects spacing)
- **Pointer to latest summary**:
  (session summary to be written on handoff)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.106 |
| act_wiz.c audit | All 44 gaps closed (`ACT_WIZ_C_AUDIT.md`) |
| Wiz parity tests | 108 passed (`test_act_wiz_command_parity.py`) |
| Full integration suite | `pytest tests/integration/ -q` — 1804 passed (1 known flaky excluded) |
| Active focus | Continue `act_wiz.c` or move to next audit target |

## Next Intended Task

Continue reviewing `act_wiz.c` for any remaining gaps, or move to the next P0/P1 file per
`ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`.
