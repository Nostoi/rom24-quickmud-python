# Session Summary — 2026-06-11 — FIGHT-056/057 regression test fix

## Scope

Continuation from the previous session (v2.14.3, FIGHT-056/057 committed). The
full test suite run at the end of that session revealed 19 regression failures
in non-integration `tests/test_*.py` files. All 19 failures had the same root
cause: the tests hardcoded pre-soft-cap damage expectations that became wrong
after FIGHT-056 moved the ROM damage soft-cap (`src/fight.c:717-720`) into
`apply_damage`. No production code changed this session — the work was
exclusively assertion updates.

## Outcomes

### 19 pre-FIGHT-056 test assertions — ✅ FIXED

- **Commit**: `8678fe38 test: update 19 pre-FIGHT-056 assertions to reflect damage soft-cap`
- **Root cause**: After FIGHT-056, `apply_damage` now applies the ROM two-tier
  soft-cap (`if dam > 35: dam = (dam-35)/2+35; if dam > 80: dam = (dam-80)/2+80`)
  before any other modifier. Tests that hardcoded raw dice values as expected
  damage now receive the correctly-capped value instead.
- **Pattern**: spell handlers return the applied (capped) damage; spell-save
  tests compute `c_div(dice, 2)` and then the cap applies to *that*; weapon
  tests compute raw multiplicative damage and then the cap applies.
- **on_hit_effects semantic**: After FIGHT-057, `on_hit_effects` is called in
  `attack_round` with post-`apply_damage_reduction` but **pre-RIV** damage (RIV
  now runs once inside `apply_damage`). The three assertions in
  `test_riv_scaling_applies_before_side_effects` that expected post-RIV values
  (4, 7, 0) now correctly assert the pre-RIV value (5).

Key cap values applied this session:
  | Raw | Cap |
  |-----|-----|
  | 36  | 35  |
  | 40  | 37  |
  | 43  | 39  |
  | 47  | 41  |
  | 48  | 41  |
  | 52  | 43  |
  | 58  | 46  |
  | 82  | 58  |
  | 88  | 61  |
  | 90  | 62  |
  | 107 | 71  |
  | 160 | 88  |
  | 240 | 108 |
  | 260 | 113 |

- **`_rom_fireball` reference function** (`test_spell_critical_gameplay_rom_parity.py`):
  added the soft-cap block so it mirrors what `apply_damage` actually does.
- **`_soft_cap` helper** added to `test_spell_area_effects_rom_parity.py` for
  the seeded-RNG holy_word tests where `expected_damage = rng_mm.dice(level, N)`.

## Files Modified

- `tests/test_combat.py` — updated 3 assertions in `test_riv_scaling_applies_before_side_effects`; pre-RIV = 5 for all three (resistant/vulnerable/immune)
- `tests/test_combat_damage_types.py` — `victim.hit` assertion: 10 → 38 (cap 90 → 62)
- `tests/test_skills.py` — `victim.hit` assertion: 84 → 85 (cap 36 → 35)
- `tests/test_skills_damage.py` — 11 assertions across ray_of_truth, general_purpose, high_explosive, fireball, lightning_bolt, energy_drain, flamestrike (×2 each for no-save and save-half)
- `tests/test_skills_mass.py` — holy_word enemy.hit: 350-240 → 350-108
- `tests/test_spell_area_effects_rom_parity.py` — added `_soft_cap` helper; updated 2 holy_word victim.hit assertions
- `tests/test_spell_breath_weapons_rom_parity.py` — general_purpose 47 → 41; high_explosive 52 → 43
- `tests/test_spell_critical_gameplay_rom_parity.py` — added soft-cap to `_rom_fireball`; fireball_damage_table expected 43 → 39

## Test Status

- 19/19 previously-failing tests: **green**
- Full suite: **5603/5603 passing, 4 skipped** (run 2026-06-11, post-regression-fix)

## Next Steps

No version bump this session (test-only change; the behavioral fix was already
captured in v2.14.2 CHANGELOG).

**FIGHT-058 (candidate, undocumented — file and close first):** Spells bypass
`apply_damage_reduction`. Spell handlers in `mud/skills/handlers.py` (fireball,
flamestrike, earthquake, energy_drain, chain_lightning, etc.) call `apply_damage`
directly, bypassing drunk/sanctuary/protect_evil/protect_good reductions. In
ROM, ALL damage through `damage()` gets these reductions at `src/fight.c:775-785`.
The fix: move `apply_damage_reduction` INTO `apply_damage` so all callers
benefit. This completes the ROM `damage()` pipeline inside Python. File as
FIGHT-058 in `docs/parity/FIGHT_C_AUDIT.md`, write failing test, implement fix,
commit.

After FIGHT-058, resume INV-044 cross-file probe on any unprobed candidate
areas (mob script triggers, group/follower chain, position transitions under
multi-attack).
