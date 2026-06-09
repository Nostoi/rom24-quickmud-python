# Session Status — 2026-06-09 — MEdit speech mobprog runtime probe (2.13.45)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **MEdit-created `TRIG_SPEECH` runtime probe covered.** An OLC-created
    `speech` mobprog now has end-to-end integration coverage through
    `_interpret_medit` → `spawn_mob` → player-facing `do_say`, confirming the
    builder-created `MobProgram` and ROM trigger bit reach runtime speech
    trigger selection with the raw spoken phrase.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_SPEECH_RUNTIME_PROBE.md](SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_SPEECH_RUNTIME_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.45 |
| Tests | 5469 passed, 5 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 18 generated-oracle tests |
| Class 11 dynamic widening | MEdit `TRIG_ENTRY` + `TRIG_GREET` + `TRIG_SPEECH` runtime paths covered |

## Next Intended Task

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. A good candidate is the sibling OLC-created `act`
mobprog runtime path, with primary ROM source read first through the room
`act()` dispatch path. Another non-combat lifecycle probe is also reasonable.
Avoid RNG-locked combat until seed alignment has its own grounded probe.
