# Session Status — 2026-06-10 — Furniture Regen Scenario + __set_on Meta-Commands (2.13.81)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`__set_on=<vnum>`, `__set_on_val3=<n>`, `__set_on_val4=<n>` meta-commands** — added to
    both `src/diff_shim/diffmain.c` and `tools/diff_harness/pyreplay.py`. `__set_on` spawns a
    furniture object and sets `ch->on`/`char.on`; the Python handler copies `prototype.value`
    to length-5 before the override (AGENTS.md spawn_object parity note).
  - **`char_update_regen_furniture` scenario** — C oracle confirms furniture `value[3]=150`
    scales HP+move (`* 150/100`), `value[4]=200` scales mana (`* 200/100`). Python already
    correct. HP+15, mana+34, move+42 per pulse. 40 smoke tests pass.
  - **`test_drive_python_replay_furniture_bonus_scales_regen`** — unit test locking the three
    furniture-bonus branches with C-oracle values.
  - **Regen scenario suite is now complete** — all 8 modifiers (POISON/PLAGUE/HASTE/SLOW/
    heal_rate/mana_rate/furniture val3/furniture val4) have C-oracle scenarios.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_FURNITURE_REGEN_SCENARIO.md](SESSION_SUMMARY_2026-06-10_FURNITURE_REGEN_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.81 |
| Tests | 5546 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced (next free ID: INV-042) |
| Diff-harness scenarios | 40 scenarios, 67 C-oracle tests passing, 0 skipped, 0 xfailed |
| FINDINGS.md highest ID | FINDING-033 (✅ RESOLVED — all findings resolved) |

## Next Intended Task

Cross-file invariants remains the active pass. The regen scenario suite is complete.

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **Next cross-INV candidate** — probe affect-tick contracts, position-transition edges, or
   group/follower chain for divergences not yet covered by an INV row (next free: INV-042).
   Method: 5-minute probe (ROM C contract → Python equivalent → one failing test), then either
   gap-closer commit or new INV-NNN in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.
