# Session Status — 2026-06-03 — INV-038 idle-timer reset on input (2.12.86)

## Current State

- **Active mode**: cross-file invariants via **probe-then-scope** under the
  divergence-class completeness lens.
- **INV-038 (idle-timer reset on input) → ✅ ENFORCED (2.12.86).**
  ROM resets a PC's idle `ch->timer` to 0 **only** on descriptor input
  (`src/comm.c:605`), reconnect, and return-from-void — never on the game tick —
  while `src/update.c:char_update` increments it once per tick for every
  non-immortal PC (void at `>= 12`, autoquit on pre-increment `> 30`). Python
  reset it on every tick for connected players and had no reset-on-input path, so
  idle→void / idle→autoquit were dead for everyone logged in.
- **Production divergence closed**: connected players never idled to the void or
  auto-quit. `mud/game_loop.py:char_update` now lets the timer climb (autosave
  decoupled), and `mud/net/connection.py:_read_player_command` resets it on input
  (shared telnet/SSH/websocket chokepoint).
- **GL-034 filed (❌ OPEN)** in `UPDATE_C_AUDIT.md`: ROM auto-quits at most one
  idle PC per tick (`ch_quit` last-wins); Python quits all candidates. Low-impact
  fan-out divergence kept out of the narrow INV-038 fix.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_INV038_IDLE_TIMER_INPUT_RESET.md](SESSION_SUMMARY_2026-06-03_INV038_IDLE_TIMER_INPUT_RESET.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.86 |
| Tests | Full suite `pytest` → 5369 passed, 4 skipped (347s parallel) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 31 active rows (INV-038 ✅ ENFORCED) |
| Divergence-class lens | Layer A 4/4 feasible; class 6 (pointer-identity) ✅ FULLY CLOSED |
| Lint / impact | `ruff check mud/game_loop.py mud/net/connection.py tests/integration/test_inv038_idle_timer_input_reset.py` clean; `gitnexus_impact` on `char_update` + `_read_player_command` LOW risk; `detect_changes(all)` LOW risk, 0 affected processes |

## Next Intended Task

Candidate next passes:

1. **GL-034** (single-quit-per-tick autoquit fan-out) — small, self-contained
   `/rom-gap-closer` candidate now filed in `UPDATE_C_AUDIT.md`.
2. **Highest-ceiling (multi-day):** `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
3. **New cross-INV probe area** — another affect-tick or group/follower-chain
   edge.
4. **Housekeeping:** INV tracker consolidation (31 active rows, past the ~20
   soft cap).
