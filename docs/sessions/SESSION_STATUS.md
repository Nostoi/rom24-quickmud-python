# Session Status — 2026-06-09 — MEdit exit/exall/grall mobprog runtime probe (2.13.52)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **MEdit-created `TRIG_EXIT` / `TRIG_EXALL` / `TRIG_GRALL` runtime probes covered.**
    All deterministic OLC-created mobprog trigger types now have end-to-end
    integration coverage through `_interpret_medit` → `spawn_mob` →
    `move_character`. EXIT confirms the position+visibility guard
    (`src/mob_prog.c:1262-1269`), EXALL confirms the unconditional dispatch
    (`src/mob_prog.c:1271-1276`), and GRALL confirms the fallback branch in
    `mp_greet_trigger` when the mob is not at `default_pos`
    (`src/mob_prog.c:1333-1345`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_EXIT_EXALL_GRALL_RUNTIME_PROBE.md](SESSION_SUMMARY_2026-06-09_MEDIT_MPROG_EXIT_EXALL_GRALL_RUNTIME_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.52 |
| Tests | 43 passed OLC-009 suite; full suite not rerun this session (previous baseline: 5474 passed, 5 skipped) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 18 generated-oracle tests |
| Class 11 dynamic widening | All deterministic MEdit trigger types covered: `TRIG_ENTRY` + `TRIG_GREET` + `TRIG_SPEECH` + `TRIG_ACT` + `TRIG_BRIBE` + `TRIG_GIVE` + `TRIG_FIGHT`/`TRIG_HPCNT` + `TRIG_SURR` + `TRIG_KILL`/`TRIG_DEATH` + `TRIG_EXIT` + `TRIG_EXALL` + `TRIG_GRALL` |

## Next Intended Task

All deterministic MEdit trigger types are now covered. Remaining Class 11 work:

1. **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — defer until seed
   alignment has a grounded probe.
2. **Diff-harness movement scenario** — author a `move_character`-based scenario
   in `tools/diff_harness/scenarios/` to give exit/greet/grall triggers C-oracle
   ground truth.
3. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
   for the next unverified surface outside Class 11.
