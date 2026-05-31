# Session Status — 2026-05-31 — GL-031 pet spell-effect persistence (2.12.10)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.10)**:
  - **GL-031 — CLOSED** (commit `1470a4ef`). A charmed pet's spell-cast buffs
    (armor/sanctuary/giant-strength) were silently lost across save/reload: the
    port keeps them in `MobInstance.spell_effects` (a `SpellEffect` dict,
    separate from the integer-SN `affected` list `_serialize_pet` walks), and
    that dict was never serialized. Added a `PetSpellEffectSave` dataclass +
    `PetSave.spell_effects` field; `_serialize_pet` serializes `pet.spell_effects`
    and `_deserialize_pet` restores them. **Primary-source correction to the
    audit's proposed fix**: restore is **data-only** (re-register the
    `SpellEffect` + mirror its shadow via `sync_spell_effect_to_affected`),
    NOT `apply_spell_effect` — ROM `fread_pet` (`src/save.c:1544-1573`) links
    each affect onto `pet->affected` *without* `affect_modify` (the saved
    `ACs`/`Hit`/`AMod` lines already fold in the bonuses), so re-applying would
    double-count. Test:
    `tests/integration/test_gl031_pet_spell_effect_persistence.py` (verified
    red-under-`apply_spell_effect`, green-under-data-only — the discriminating
    check that locks the contract).
  - **GL-032 — FILED (OPEN)** (commit `83ea8850`). Advisor review while closing
    GL-031 surfaced that `MobInstance.apply_spell_effect`
    (`mud/spawning/templates.py`) is a "simplified" applier that only applies
    `hitroll_mod`/`damroll_mod`/`affect_flag` — it ignores `ac_mod`,
    `saving_throw_mod`, `stat_modifiers`, and `sex_delta`. ROM applies every
    affect location via `affect_modify` (`src/handler.c`), and
    `Character.apply_spell_effect` does too, so a charmed pet buffed with armor
    (AC), giant strength (STR), or a save-modifying spell currently gains
    nothing except hitroll/damroll — both live and (consistently) on reload.
    See `UPDATE_C_AUDIT` GL-032.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-31_GL031_PET_SPELL_EFFECT_PERSISTENCE.md](SESSION_SUMMARY_2026-05-31_GL031_PET_SPELL_EFFECT_PERSISTENCE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.10 |
| Tests | 5131 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced |
| Open correctness gaps | One filed (OPEN): **GL-032** (`UPDATE_C_AUDIT` — `MobInstance.apply_spell_effect` ignores ac/saving/stat/sex affect locations; charmed pets get no AC/stat benefit from buffs). GL-031 closed (2.12.10). |
| Active focus | cross-file invariants probe pass |

## Next Intended Task

GL-031 closed. Two options for the next session:

1. **Close GL-032** (`rom-gap-closer GL-032`) — bring
   `MobInstance.apply_spell_effect`/`remove_spell_effect` to parity with
   `Character`'s (apply/unwind ac/saving/stat/sex affect locations), or share
   the implementation. This is a behavioral change that affects **all** NPC
   buffs, not just pets — run the combat/affect suites and weigh RNG-stream
   implications (mob affects now tick on the main GL-026/GL-027 path).
2. **Resume the cross-file-invariants probe pass** — remaining candidates:
   position transitions, group/follower chain, and the broader INV-025 sweep
   (non-combat `_push_message`/`broadcast_room` narration where the matching
   ROM site uses `act()`).

Method: probe-then-scope (read ROM C contract → read Python equivalent →
one failing test for the contract → close as a gap or file as next INV-NNN).
