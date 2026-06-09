# Session Status — 2026-06-09 — MEdit surrender mobprog runtime probe (2.13.50)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **MEdit-created `TRIG_SURR` runtime probe covered.**
    OLC-created surrender mobprogs now have end-to-end integration coverage
    through `_interpret_medit` → `spawn_mob` → `do_surrender`, confirming the
    builder-created `MobProgram` row and ROM trigger bit reach the player-facing
    surrender dispatch path before the NPC ignore/retaliation fallback.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_SURR_RUNTIME_PROBE.md](SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_SURR_RUNTIME_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.50 |
| Tests | 5474 passed, 5 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 18 generated-oracle tests |
| Class 11 dynamic widening | MEdit `TRIG_ENTRY` + `TRIG_GREET` + `TRIG_SPEECH` + `TRIG_ACT` + `TRIG_BRIBE` + `TRIG_GIVE` + `TRIG_FIGHT`/`TRIG_HPCNT` + `TRIG_SURR` runtime paths covered |

## Next Intended Task

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are MEdit-created `death` / `kill`
runtime probes or an exit/exall probe that avoids relying on movement RNG.
Avoid RNG-locked combat until seed alignment has its own grounded probe.
