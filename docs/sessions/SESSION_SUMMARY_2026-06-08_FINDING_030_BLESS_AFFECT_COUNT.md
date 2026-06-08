# Session Summary — 2026-06-08 — FINDING-030: bless zero-modifier AffectData count (2.13.25)

## Scope

Picked up from the 2.13.24 handoff's "Close FINDING-030" task. The bug: at `char_level ≤ 7`,
`c_div(level, 8) == 0` so `bless` passes `hitroll_mod=0` and `saving_throw_mod=0` to
`SpellEffect`. Python's `sync_spell_effect_to_affected` used falsy guards (`if effect.hitroll_mod:`)
that skipped zero-valued entries — falling through to the APPLY_NONE fallback and emitting 1
AffectData instead of 2. ROM C (`src/magic.c:849–860`) calls `affect_to_char` twice
unconditionally, producing 2 AFFECT_DATA nodes regardless of modifier value. This caused 1
extra `number_range(0,4)` RNG call per `char_update` tick in C (vs Python) when bless was active
at low levels — diverging the RNG state for any operation after a tick.

## Outcomes

### FINDING-030 — `bless` zero-modifier AffectData count — ✅ RESOLVED

- **Python**: `mud/models/character.py:sync_spell_effect_to_affected` (guard was `if effect.hitroll_mod:`)
- **ROM C**: `src/magic.c:849–860` (two unconditional `affect_to_char` calls)
- **Root cause**: `SpellEffect.hitroll_mod` / `saving_throw_mod` defaults were `int = 0`;
  the falsy guard treated "explicitly zero" the same as "not set", skipping APPLY_HITROLL and
  APPLY_SAVES entries for bless at low levels.
- **Fix**:
  - `SpellEffect.hitroll_mod` / `saving_throw_mod` defaults changed `0 → None` (`int | None`).
  - Guards in `sync_spell_effect_to_affected` updated `if x:` → `if x is not None:`. Bless
    passes `hitroll_mod=0` explicitly so `0 is not None` → APPLY_HITROLL entry emitted. Spells
    that never set these fields (e.g. `armor`) get `None` → guard correctly suppresses emission
    (regression guard confirmed: armor still emits exactly 1 APPLY_AC entry).
  - `_add_opt(a, b)` helper added for None-safe merge arithmetic in `Character.apply_spell_effect`
    and `MobInstance.apply_spell_effect` (the `combined.hitroll_mod += existing.hitroll_mod`
    paths that run on affect-join / re-cast).
  - `PetSpellEffectSave.hitroll_mod` / `saving_throw_mod` changed to `int | None = None`;
    `_serialize_pet` updated to preserve None explicitly (was `_safe_int(...)` which collapsed
    None to 0, which would have spuriously triggered APPLY_HITROLL on reload for armor-buffed pets).
  - `MobInstance.remove_spell_effect` guards simplified from `getattr(effect, "hitroll_mod", 0)`
    to `effect.hitroll_mod` (direct access; Pyright narrows `int | None` to `int` in truthy branch).
- **Tests**: 3 new integration tests in `tests/integration/test_finding030_bless_affect_count.py`:
  - `test_bless_low_level_emits_two_affect_data_entries` — bless@level5: 2 entries at
    APPLY_HITROLL(18) + APPLY_SAVES(20), both modifier=0. Failed before fix (got `{0}` / APPLY_NONE).
  - `test_bless_high_level_still_emits_two_affect_data_entries` — bless@level16: 2 entries,
    modifiers +2/-2 (non-zero path didn't regress). Passed before and after fix.
  - `test_armor_still_emits_only_one_affect_data_entry` — armor: exactly 1 entry at APPLY_AC(17).
    Passed before and after fix (key regression guard for None-default).

## Files Modified

- `mud/models/character.py` — `SpellEffect` field types (`int | None`), `_add_opt` helper,
  `sync_spell_effect_to_affected` guards, `Character.apply_spell_effect` merge arithmetic
- `mud/spawning/templates.py` — `MobInstance.apply_spell_effect` merge arithmetic (`_add_opt`),
  `MobInstance.remove_spell_effect` direct attribute access
- `mud/db/serializers.py` — `PetSpellEffectSave` field types, `_serialize_pet` None-preservation
- `tests/integration/test_finding030_bless_affect_count.py` — new test file (3 tests)
- `tools/diff_harness/FINDINGS.md` — FINDING-030 status: ⚠️ OPEN → ✅ RESOLVED
- `CHANGELOG.md` — added 2.13.25 section (Fixed + Tests entries)
- `pyproject.toml` — 2.13.24 → 2.13.25

## Test Status

- **FINDING-030 tests**: 3/3 passing (`tests/integration/test_finding030_bless_affect_count.py`)
- **Integration suite**: 2835 passed, 3 skipped, 0 failed
- **Full suite**: 5441 passed, 4 skipped, 0 failed
- `ruff check .` clean; `gitnexus_detect_changes` LOW risk, 0 affected processes

## Outstanding

- **Pre-existing DB rows**: Pet `SpellEffect` entries serialized before this fix have
  `hitroll_mod: 0` (not `None`) in the JSON. On reload `PetSpellEffectSave.hitroll_mod=0` →
  `SpellEffect.hitroll_mod=0` → `is not None` → APPLY_HITROLL entry emitted spuriously for
  spells like `armor` that should have `hitroll_mod=None`. A DB migration would be needed to
  null out these fields, but in-flight pet saves are transient (pets don't persist across engine
  restarts in normal play); deferred. Noted for future if save/reload parity becomes a test target.

## Next Steps

1. **Shop transaction atomicity** — probe insufficient-funds and item-not-for-sale error-exit
   paths in `do_buy` / `do_sell`. A scenario with a player holding exactly 0 silver buying a
   300-silver item isolates the error path. These are candidates for INV entries (cross-file
   contracts: wealth deduction should be atomic with inventory transfer).
2. **Cross-INV: affect-tick ordering** — verify `char_update` processes affects in the same order
   as ROM C (`src/update.c:char_update`), specifically `affect_remove` vs `affect_update` call
   ordering for multi-affect characters.
3. **Diff-harness: bless + tick RNG** — now that FINDING-030 is closed, consider adding a
   diff-harness Hypothesis rule that casts bless at a low-level character and ticks, to lock
   the RNG parity in a machine-checked scenario (currently only integration-tested).
