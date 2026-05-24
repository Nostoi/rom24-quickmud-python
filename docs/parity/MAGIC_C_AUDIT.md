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

## Scope Notes

- Object-targeted spells (`"object"` JSON, ROM `TAR_OBJ_INV` and the
  object branches of `TAR_OBJ_CHAR_*`) are not yet routed by
  `do_cast` — the fix routes those to `target = char` as a
  placeholder. Filed as future work; tracker once audited.
- The `is_safe` / `check_killer` PK gates (ROM src/magic.c:397-413)
  are still not enforced from the Python `do_cast` path. Filed as
  future work; tracker once audited.
