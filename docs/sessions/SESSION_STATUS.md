# Session Status — 2026-06-10 — FIGHT-043 do_flee XP loss + MATH-002/003/004 c_div hygiene

## Current State

- **Active audit**: Cross-file invariants pass (all per-file audits complete at 100% P0/P1/P2)
- **Last completed**: MATH-002/003/004 (c_div hygiene, 2.13.86), FIGHT-043 (do_flee XP block, 2.13.87)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-10_MATH002_004_FIGHT043_FLEE_XP.md](SESSION_SUMMARY_2026-06-10_MATH002_004_FIGHT043_FLEE_XP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.87 |
| Tests | 2892 integration passed, 3 skipped |
| ROM C files audited | 43 / 43 (all P0/P1/P2 at 100%; P3 at 75% + 3 N/A) |
| Cross-file INVs enforced | 28 (next free: INV-044) |
| Active focus | Cross-file invariants — `do_flee`/`do_recall` area closed; next: `stop_fighting` caller survey |

## Next Intended Task

Cross-file invariants remains the active pass. Three probe candidates resolved this session
(INV-015 affect-expiry clean, do_flee/do_recall ordering clean, MATH-002/003/004 fixed).
FIGHT-043 (`do_flee` missing XP block) is now closed.

Suggested next probes:

1. **`stop_fighting` caller survey** — grep all call sites in `mud/` not yet guarded by an INV
   row (spell-interrupt paths, skill-abort paths, logout paths). Compare against ROM
   `src/handler.c:stop_fighting` callers. Any call where `both=False` is passed but ROM
   passes `TRUE`, or where `stop_fighting` is absent, is a candidate INV.

2. **`do_flee` / `do_recall` position reset after move** — ROM `src/act_move.c:do_recall`
   sets `ch->position = POS_STANDING` explicitly after relocating the character. Confirm
   Python `do_flee` and `do_recall` reset `char.position` to `Position.STANDING` post-move.
   A quick read of combat.py + session.py do_recall suffices.

3. **`check_killer` call-site completeness** — FIGHT-030 closed the `do_rescue` gap.
   Verify `do_murder` and `do_kill` paths have equivalent `check_killer` calls. Low-risk
   but easy 5-minute probe.
