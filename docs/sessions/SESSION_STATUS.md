# Session Status — 2026-06-19 — INV-050 gate cleared (`is_safe_spell` standalone)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). This session closed the **INV-050 gate** by making
  `is_safe_spell` a faithful standalone port of ROM `src/fight.c:1126-1218`.
- **Last completed** (this session, 1 parity commit + handoff docs):
  - **INV-050 gate CLEARED** (2.14.132, `d3c91e4a`) — `mud/combat/safety.py:is_safe_spell`
    no longer delegates to the divergent silent `is_safe` bool; it is now a
    faithful standalone port of ROM's separate `is_safe_spell` (retaliation
    bypass before NPC ROOM_SAFE, immortal/area bypasses, legal-kill
    `is_same_group` clauses, PC-vs-PC clan PK ladder). Fixes `do_cast`'s
    TAR_OBJ_CHAR_OFF gate (`src/magic.c:484`). `handlers.py:_is_safe_spell` now
    delegates to it (de-duped). 4 tests; corrected one stale KILLER test.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_INV050_IS_SAFE_SPELL_STANDALONE.md](SESSION_SUMMARY_2026-06-19_INV050_IS_SAFE_SPELL_STANDALONE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.132 |
| Tests | Area suites green (119 passed this turn); full suite green (exit 0) with the 4 new INV-050 tests |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep |

## Next Intended Task

INV-050's gate is cleared, so the remaining INV-050 task is **unblocked**:
collapse `is_safe`'s callers onto the faithful `_kill_safety_message` mirror (or
make the silent bool a thin wrapper), leaving only the intentionally-silent
`apply_damage` re-check (FIGHT-002, `combat/engine.py`) on the raw bool. Other
open follow-ups: `mud/entrypoint.py` dead code. The higher-yield
enumeration-independent lever per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` is the
Hypothesis state-machine → diff_harness widening (Class 11 mobprog paths
complete; open frontier is non-mobprog scenario coverage).
