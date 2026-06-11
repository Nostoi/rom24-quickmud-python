# Session Status — 2026-06-11 — FIGHT-056/057 damage soft-cap + double-RIV closed

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-056 (`mud/combat/engine.py:apply_damage` — added ROM
  `src/fight.c:717-720` two-tier damage soft-cap before `is_safe`; 200 raw → 98 capped,
  50 raw → 42 capped, affects all callers) and FIGHT-057 (`mud/combat/engine.py:attack_round`
  — removed duplicate RIV application that was causing double-resistance for weapon attacks;
  IS_RESISTANT now correctly reduces by 1/3 once, not twice)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-11_FIGHT056_057_DAMAGE_SOFTCAP_DOUBLE_RIV.md](SESSION_SUMMARY_2026-06-11_FIGHT056_057_DAMAGE_SOFTCAP_DOUBLE_RIV.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.3 |
| Tests | 2936/2939 integration passing, 3 skipped (2026-06-11) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

**FIGHT-058 (candidate, undocumented — file and close first):** Spells bypass
`apply_damage_reduction`. Spell handlers in `mud/skills/handlers.py` (fireball, flamestrike,
earthquake, energy_drain, chain_lightning, etc.) call `apply_damage` directly, bypassing
drunk/sanctuary/protect_evil/protect_good reductions. In ROM, ALL damage through `damage()`
gets these reductions at `src/fight.c:775-785`. The fix: move `apply_damage_reduction` INTO
`apply_damage` so all callers benefit. This completes the ROM `damage()` pipeline inside Python.
File as FIGHT-058 in `docs/parity/FIGHT_C_AUDIT.md`, write failing test, implement fix, commit.

After FIGHT-058, resume INV-044 cross-file probe on any unprobed candidate areas (mob script
triggers, group/follower chain, position transitions under multi-attack).

Noted additional probes that were clean this session:
- `group_gain` NPC-level floor — no gap
- `apply_damage` death-message broadcast — no gap
- zero-dam WEAPON_NONE path — no gap
