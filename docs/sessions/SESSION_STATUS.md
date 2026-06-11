# Session Status — 2026-06-10 — INV-042 Kill-Death-XP-Trigger Ordering (2.13.84)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **INV-042 KILL-DEATH-XP-TRIGGER-ORDERING** — filed and locked the three-step call-order
    contract in `mud/combat/engine.py:_handle_death`: `group_gain` → `mp_death_trigger` →
    `raw_kill`. ROM `src/fight.c:883-924`. Two mutation-verified call-order spy tests in
    `tests/integration/test_inv042_kill_death_xp_trigger_ordering.py`. Cross-file tracker now
    27 enforced INVs; next free ID: **INV-043**.
  - **mob_update loop contracts probe** — confirmed no gap. Python `mud/ai/__init__.py:mobile_update`
    uses `list(character_registry)` snapshot equivalent to ROM's `ch_next` pre-cache in
    `src/update.c:mobile_update` (starts at line 408, not 893). INV-017 covers the same pattern
    for `char_update`; no new row needed.
  - Previous session's INV-006 position-ordering sub-contract (stop_fighting ordering,
    mutation-verified at v2.13.83).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_INV042_KILL_DEATH_XP_TRIGGER_ORDERING.md](SESSION_SUMMARY_2026-06-10_INV042_KILL_DEATH_XP_TRIGGER_ORDERING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.84 |
| Tests | 5552 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 27 enforced (next free ID: INV-043) |
| Diff-harness scenarios | 40 scenarios, 67 C-oracle tests passing, 0 skipped, 0 xfailed |
| FINDINGS.md highest ID | FINDING-033 (✅ RESOLVED — all findings resolved) |

## Next Intended Task

Cross-file invariants remains the active pass.

1. **Group XP penalty signed-math site** — `_handle_death` lines 1352-1358 computes
   `c_div(2 * (floor - victim.exp), 3) + 50`; `floor - victim.exp` is negative when the PC
   is over the floor. Verify `c_div` is used (it is) and that this specific signed-math site
   is covered by a test or noted in MATH_AND_RNG.md under MATH-002/003/004. Probe method:
   read `src/fight.c:887-893` → `mud/combat/engine.py:1352-1358` → confirm `c_div` call.

2. **`char_update` autosave slot coherence** — ROM `src/update.c:686-700` fans out PC saves
   via a `save_number` modulo. Python `mud/game_loop.py:char_update` has an equivalent; the
   cross-file contract (slot distribution + `desc is not None` gate) is not locked by any INV.
   INV-038 covers idle-timer reset but not the save-slot fan-out.

3. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
