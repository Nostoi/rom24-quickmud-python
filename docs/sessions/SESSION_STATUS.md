# Session Status — 2026-06-09 — Diff-harness TRIG_EXALL + TRIG_GREET/GRALL + position suffix fix (2.13.54)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **TRIG_EXALL C-oracle ground truth.** `mob_movement_triggers_exall.json` confirms
    EXIT is gated on `mob->position == default_pos && can_see`, while EXALL fires
    unconditionally (`src/mob_prog.c:1262-1276`). Python and C agree.
  - **TRIG_GREET/GRALL C-oracle ground truth.** `mob_movement_triggers_greet_grall.json`
    confirms GREET fires at `default_pos`, GRALL is the else-if fallback
    (`src/mob_prog.c:1325-1345`). Python and C agree.
  - **`_room_occupant_line` position suffix parity fix.** Mobs at non-default positions
    now render with ROM-correct suffix + initial-cap, matching `show_char_to_char_0`
    (`src/act_info.c:247-424`). Dark-room path also fixed.
  - **`__mob_position=<pos>` meta-command** added to C shim and Python pyreplay.
  - **`__mob_prog` LIFO ordering** fixed in pyreplay (was FIFO, ROM C prepends).
  - Version 2.13.54; 5,481 tests pass.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_EXALL_GREET_GRALL_POSITION_SUFFIX.md](SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_EXALL_GREET_GRALL_POSITION_SUFFIX.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.54 |
| Tests | 5,481 passed, 5 skipped (last full run) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 12 static scenarios; 21+ golden tests; all findings resolved |
| Class 11 dynamic widening | EXIT + EXALL + GREET + GRALL deterministic paths all have C-oracle ground truth |

## Next Intended Task

Class 11 remaining work (in priority order):

1. **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — requires seed alignment grounded
   probe before a meaningful C-oracle scenario can be authored. Defer until there is a
   reproducible seed sequence for those paths.
2. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the next
   unverified surface outside Class 11. Candidates include async message delivery ordering,
   affect-tick edge contracts, and position-transition invariants.
3. **Class 11 completeness check** — SPEECH, ACT, BRIBE, GIVE mobprog dispatch paths still
   lack C-oracle scenarios. Consider adding deterministic variants (no-RNG-gate variants)
   before tackling the RNG-locked ones.
