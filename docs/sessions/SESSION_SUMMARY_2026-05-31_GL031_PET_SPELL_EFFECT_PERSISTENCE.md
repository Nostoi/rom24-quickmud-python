# Session Summary — 2026-05-31 — GL-031 pet spell-effect persistence

## Scope

Picked up from the GL-027 mob affect-tick handoff (`SESSION_STATUS.md` listed
**GL-031** as the single remaining open correctness gap). Closed GL-031 — a
charmed pet's spell-cast buffs were silently lost across save/reload — via the
standard gap-closer TDD flow (failing test → fix → tracker/changelog → commit).
Advisor review while closing it surfaced a related but distinct divergence in
the mob affect applier, filed as **GL-032**.

## Outcomes

### `GL-031` — ✅ FIXED (2.12.10, commit `1470a4ef`)

- **Python**: `mud/db/serializers.py` — `_serialize_pet` / `_deserialize_pet`,
  new `PetSpellEffectSave` dataclass + `PetSave.spell_effects` field.
- **ROM C**: `src/save.c:508-517` (`fwrite_pet`), `src/save.c:1544-1573`
  (`fread_pet`).
- **Gap**: GL-031 — the port keeps spell-cast pet buffs in
  `MobInstance.spell_effects` (a `SpellEffect` dict, separate from the
  integer-SN `affected` list `_serialize_pet` walks); that dict was never
  serialized, so a charmed pet buffed with armor/sanctuary/giant-strength lost
  the buff on reload (GL-030 correctly skips the string-named shadow
  `AffectData`, but nothing else carried them).
- **Fix**: added `PetSpellEffectSave` + `PetSave.spell_effects`;
  `_serialize_pet` serializes `pet.spell_effects` and `_deserialize_pet`
  restores them. **Primary-source correction to the audit's proposed fix**:
  restore is **data-only** (re-register the `SpellEffect` + mirror its shadow
  via `sync_spell_effect_to_affected`), **not** `apply_spell_effect` — ROM
  `fread_pet` links each affect onto `pet->affected` *without* `affect_modify`
  (the saved `ACs`/`Hit`/`AMod` lines already fold in the bonuses), so
  re-applying would double-count the modifiers against the already-modified
  saved stats.
- **Tests**: `tests/integration/test_gl031_pet_spell_effect_persistence.py`
  (1 test, passing). Round-trips armor/sanctuary/giant-strength/bless through
  the JSON dict form. After advisor review, added a `hitroll_mod`/`damroll_mod`
  buff (`bless`) so the "no double-application" assertion is non-vacuous, and
  **verified red-under-`apply_spell_effect`** (`hitroll == 4` vs saved `2`) /
  green-under-data-only — the discriminating check that locks the contract.

### `GL-032` — ⚠️ FILED (commit `83ea8850`, OPEN)

- **Python**: `mud/spawning/templates.py` — `MobInstance.apply_spell_effect` /
  `remove_spell_effect`.
- **ROM C**: `src/handler.c` `affect_modify` (applies every affect location).
- **Gap**: `MobInstance.apply_spell_effect` is a "simplified" applier that only
  applies `hitroll_mod`/`damroll_mod`/`affect_flag` — it ignores `ac_mod`,
  `saving_throw_mod`, `stat_modifiers`, and `sex_delta`. ROM applies all
  locations uniformly via `affect_modify`, and `Character.apply_spell_effect`
  does too, so a charmed pet (NPC) buffed with armor (AC), giant strength
  (STR), or a save-modifying spell currently gains nothing except
  hitroll/damroll — both live and (consistently) on reload.
- **Surfaced by**: advisor review while closing GL-031 (the ac_mod /
  stat_modifier round-trip assertions were non-mutating *because* the mob
  applier ignores those locations).
- **Fix (deferred)**: bring `MobInstance.apply_spell_effect` /
  `remove_spell_effect` to parity with `Character`'s, or share the
  implementation.

## Files Modified

- `mud/db/serializers.py` — `PetSpellEffectSave` dataclass, `PetSave.spell_effects`
  field, serialize/restore loops in `_serialize_pet`/`_deserialize_pet`.
- `tests/integration/test_gl031_pet_spell_effect_persistence.py` — new
  regression (round-trip + discriminating no-double-apply check).
- `docs/parity/UPDATE_C_AUDIT.md` — GL-031 flipped ⚠️ OPEN → ✅ FIXED; new
  GL-032 ⚠️ OPEN row.
- `CHANGELOG.md` — added `Fixed: GL-031` entry under `[Unreleased]`.
- `pyproject.toml` — 2.12.9 → 2.12.10.

## Test Status

- `tests/integration/test_gl031_pet_spell_effect_persistence.py` — 1/1 passing
  (verified red-under-wrong-restore, green-under-data-only).
- Persistence/pet/account area sweep (`-k "pet or save_character or persistence
  or serial or account or charmed or follower"`) — 192/192 passing.
- GL family + pet round-trip (GL-027/028/030/031) — 7/7 passing.
- `ruff check mud/db/serializers.py` — 0 new errors (20 pre-existing in-file,
  identical on master).
- `gitnexus_detect_changes` — LOW risk, `affected_count: 0` (scope confined to
  `_serialize_pet`/`_deserialize_pet`/`PetSave` + the audit doc).
- Full suite: 5131 passed, 4 skipped.

## Next Steps

No open correctness gaps except the freshly-filed **GL-032** (mob affect applier
ignores ac/saving/stat/sex mods). Two options for the next session:

1. **Close GL-032** (`rom-gap-closer GL-032`) — bring
   `MobInstance.apply_spell_effect`/`remove_spell_effect` to parity with
   `Character`'s (apply/unwind ac/saving/stat/sex), or share the implementation.
   Note this is a behavioral change that affects all NPC buffs, not just pets —
   run the combat/affect suites and consider RNG-stream implications.
2. **Resume the cross-file-invariants probe pass** — remaining candidates:
   position transitions, group/follower chain, and the broader INV-025 sweep
   (non-combat `_push_message`/`broadcast_room` narration where the matching ROM
   site uses `act()`). Per-file audit tracker remains exhausted; cross-file
   invariants is the active mode.
