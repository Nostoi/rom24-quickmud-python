# Session Status — 2026-06-10 — INV-006 Position-Ordering Sub-Contract (2.13.83)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **INV-006 position-ordering sub-contract** — extended INV-006's enforcement
    test file with two new mutation-verified tests that lock the ordering inside
    `stop_fighting`: `fch->position = default_pos/STANDING` must come BEFORE
    `update_pos(fch)` so negative-HP characters end at their HP-driven position
    (DEAD/INCAP/etc.) rather than the reset default. NPC with `hit=0` → DEAD;
    PC with `hit=-5` → INCAP. Mutation check confirmed both go RED when the
    lines are swapped. INV-006 tracker row updated with sub-contract description
    and cross-ref to INV-019 (the upward direction: STUNNED → STANDING on heal).
  - Previous session's affect-tick probe found INV-015 already covers GL-026 and
    msg_off dedup sub-contracts (locked at v2.13.61); no new work needed.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_INV006_POSITION_ORDERING.md](SESSION_SUMMARY_2026-06-10_INV006_POSITION_ORDERING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.83 |
| Tests | 5550 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced (next free ID: INV-042) |
| Diff-harness scenarios | 40 scenarios, 67 C-oracle tests passing, 0 skipped, 0 xfailed |
| FINDINGS.md highest ID | FINDING-033 (✅ RESOLVED — all findings resolved) |

## Next Intended Task

Cross-file invariants remains the active pass. Both previous probe candidates now closed.

1. **`mob_update` loop contracts** — ROM `src/update.c:893-983` iterates `char_list`
   with `ch_next` pre-cache (snapshot-safe). Mob AI (aggressive/scavenge/wander) runs
   inside. Cross-file contract: Python `mob_update` in `mud/game_loop.py` must use a
   registry snapshot equivalent to `ch_next` so mid-iteration extraction doesn't skip
   mobs. INV-017 already covers `char_update`'s snapshot; mob_update is the parallel
   path not yet explicitly locked. Probe method: read `src/update.c:893-983` →
   `mud/game_loop.py:mob_update` → one failing test → INV-042 or gap-closer commit.

2. **Group XP delivery ordering** — `group_gain` runs before `TRIG_DEATH` in `raw_kill`;
   INV-031 covers group preservation on death but not the XP-then-trigger ordering.

3. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
