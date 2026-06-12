# Session Summary — 2026-06-11 — FIGHT-058: damage reduction bypass for spells/skills

## Scope

Continuation from v2.14.3 (FIGHT-056/057 closed, regression tests fixed). The
session picked up the FIGHT-058 candidate identified at the end of the previous
session: every spell handler in `mud/skills/handlers.py` that calls `apply_damage`
directly (fireball, flamestrike, earthquake, energy_drain, chain_lightning,
lightning_bolt, magic_missile, ray_of_truth, cause_*, etc.) bypassed the ROM
drunk/sanctuary/protection reductions because `apply_damage_reduction` was only
called from `one_hit` (the melee weapon path). The gap was filed, tested, fixed,
and committed in one session.

## Outcomes

### `FIGHT-058` — ✅ FIXED

- **Python**: `mud/combat/engine.py:apply_damage` + `mud/combat/engine.py:attack_round` (formerly `one_hit`)
- **ROM C**: `src/fight.c:775-785`
- **Gap**: FIGHT-058 — `apply_damage_reduction` (drunk/sanctuary/protection) only
  called from `one_hit`; all `apply_damage` callers (25+) including every spell
  handler bypassed reductions entirely.
- **Fix**: Moved `apply_damage_reduction` call INTO `apply_damage` (after `is_safe`,
  before parry/dodge — matching ROM order: modifiers at fight.c:775-785 precede
  parry/dodge at fight.c:793-801). Removed the now-redundant pre-call from `one_hit`
  to prevent double-reduction on the melee path.
- **Tests**: `tests/integration/test_fight058_damage_reduction_bypass.py` (4 tests):
  spell sanctuary halves damage; spell drunk reduces to 9/10; spell protect_evil
  reduces by 1/4; melee no double-reduce. All 4 verified red before fix, green after.

This completes the ROM `damage()` pipeline inside `apply_damage`:
- FIGHT-056: soft-cap (fight.c:717-720) — ✅ FIXED (2.14.2)
- FIGHT-057: RIV applied exactly once (fight.c:804-816) — ✅ FIXED (2.14.3)
- FIGHT-058: drunk/sanctuary/protection applied for all callers (fight.c:775-785) — ✅ FIXED (2.14.4)

## Files Modified

- `mud/combat/engine.py` — added `apply_damage_reduction(attacker, victim, damage)` inside
  `apply_damage` (3 lines, after `is_safe` block); removed pre-call from `one_hit` (2 lines)
- `tests/integration/test_fight058_damage_reduction_bypass.py` — new file, 4 integration tests
- `docs/parity/FIGHT_C_AUDIT.md` — filed and flipped FIGHT-058 row (🔄 OPEN → ✅ FIXED 2.14.4)
- `CHANGELOG.md` — added `[2.14.4]` Fixed entry
- `pyproject.toml` — 2.14.3 → 2.14.4

## Test Status

- `pytest tests/integration/test_fight0*.py -v` — 72/72 passing
- Full suite: **5607/5607 passing, 4 skipped** (run 2026-06-11, post-fix)

## Next Steps

FIGHT-056/057/058 complete the ROM `damage()` pipeline. Next session should probe
the **INV-044 cross-file invariant candidates**:

1. **Mob script triggers** — `mprog.mp_kill_trigger` / `mp_death_trigger` ordering
   relative to `raw_kill` and `group_gain`; does Python match ROM's exact sequence?
2. **Group/follower chain** — group membership mutation (add/remove) while combat
   iterates `room.people`; potential iterator-invalidation class.
3. **Position transitions under multi-attack** — if a victim goes to DEAD mid-round
   (e.g. via an AoE), does Python correctly stop further swings the way ROM does?

Probe method per AGENTS.md: read ROM C contract → read Python equivalent → write
one failing test per contract → either close as a gap or file as INV-NNN.
