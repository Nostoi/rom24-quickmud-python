# magic.c — Spell Engine Parity Audit

**Status**: 🔄 STUB — created 2026-05-24 to track CAST-001. Full
file-level audit of `src/magic.c` (3000+ lines covering `do_cast`,
`say_spell`, `cast_spell`, `obj_cast_spell`, `do_recite`/`do_brand`,
`do_dispel`, plus the per-spell handlers) is **not yet performed**.
Run `/rom-parity-audit magic.c` to populate the full gap table.

## Gap Table

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `CAST-001` | CRITICAL | src/magic.c:301-536 | mud/commands/combat.py:704 (`do_cast`) | `do_cast` target resolution did not honor `skill.target` (ROM `TAR_*`). With no `arg2`, Python defaulted `target = char` for every spell, so an offensive spell cast mid-combat (`cast 'magic missile'` while `ch->fighting != NULL`) hit the caster instead of the fighting victim (`Your magic missile scratches you.`). ROM `TAR_CHAR_OFFENSIVE` defaults `victim = ch->fighting` and errors `"Cast the spell on whom?"` when not fighting; `TAR_CHAR_DEFENSIVE` defaults to self; `TAR_CHAR_SELF` accepts only self; `TAR_IGNORE` ignores arg2. Fix: dispatch on `skill.target` (`"victim"` / `"character_or_object"` → fighting default; `"friendly"` → self default; `"self"`/`"ignore"` → caster). Tests: `tests/test_skills_spells_cast_listing.py::test_do_cast_offensive_no_target_defaults_to_fighting_victim`, `::test_do_cast_offensive_no_target_no_fight_errors`. | ✅ FIXED (2.8.76) |
| `MAGIC-002` | MEDIUM | src/magic.c:753-777 (`spell_armor`) | mud/skills/handlers.py:1335 (`armor`) | **Affect spells emit no ROM success message when cast through `do_cast`.** Surfaced by the differential harness `affect_armor` scenario (FINDING-015). ROM `spell_armor` sends `"You feel someone protecting you."` to the victim on success (and `act("$N is protected by your magic.")` to the caster when `ch != victim`); the Python `armor` handler applies the −20 AC affect but is **silent** on success. Since `do_cast` is silent on a successful cast (`CAST`/FINDING-013 — all output comes from the spell function), the line is dropped entirely. The affect itself is correct (affects/eff_ac/mana all converge in the differential); only the player-facing message diverges. The Python already-affected branch also sends the non-ROM `"They are already protected."` vs ROM's `"You are already armored."`. **Class, not one-off:** `bless` (handlers.py:1465) and `shield` (handlers.py:7094) are likewise silent on success — every affect-only spell cast via `do_cast` is missing its ROM success line (sweep is follow-up; this row fixes the `armor` instance). | ✅ FIXED (armor, 2.11.20) — bless/shield sweep still OPEN |

## Scope Notes

- Object-targeted spells (`"object"` JSON, ROM `TAR_OBJ_INV` and the
  object branches of `TAR_OBJ_CHAR_*`) are not yet routed by
  `do_cast` — the fix routes those to `target = char` as a
  placeholder. Filed as future work; tracker once audited.
- The `is_safe` / `check_killer` PK gates (ROM src/magic.c:397-413)
  are still not enforced from the Python `do_cast` path. Filed as
  future work; tracker once audited.
