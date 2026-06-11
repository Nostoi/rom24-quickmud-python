# Session Status — 2026-06-11 — FIGHT-056/057 regression test fix

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-056/057 regression test fix — corrected 19 pre-soft-cap
  assertions across 8 test files; suite is fully green at 5603/5603 passing
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-11_FIGHT056_057_REGRESSION_TEST_FIX.md](SESSION_SUMMARY_2026-06-11_FIGHT056_057_REGRESSION_TEST_FIX.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.3 |
| Tests | 5603/5603 passing, 4 skipped (2026-06-11) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

**FIGHT-058 (candidate, undocumented — file and close first):** Spells bypass
`apply_damage_reduction`. Spell handlers in `mud/skills/handlers.py` (fireball,
flamestrike, earthquake, energy_drain, chain_lightning, etc.) call `apply_damage`
directly, bypassing drunk/sanctuary/protect_evil/protect_good reductions. In
ROM, ALL damage through `damage()` gets these reductions at `src/fight.c:775-785`.
The fix: move `apply_damage_reduction` INTO `apply_damage` so all callers
benefit. This completes the ROM `damage()` pipeline inside Python. File as
FIGHT-058 in `docs/parity/FIGHT_C_AUDIT.md`, write failing test, implement fix,
commit.

After FIGHT-058, resume INV-044 cross-file probe on any unprobed candidate areas
(mob script triggers, group/follower chain, position transitions under
multi-attack).
