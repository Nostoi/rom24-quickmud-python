# Session Status — 2026-06-01 — MAGIC-007 object-`$p` PERS masking (2.12.31)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted) —
  INV-025 / INV-027 PERS-masking sweep.
- **Last completed (this session, 2.12.31)**:
  - **MAGIC-007 — object-`$p` spell room lines mask via `can_see_obj`.**
    Converted ~16 visible-object `$p` room broadcasts in
    `mud/skills/handlers.py` from the baked-name module-level `_act_room` to the
    shared `act_to_room("$p ..."/"$n ... $p", actor, arg1=obj)` helper, so `$p`
    renders per recipient through `can_see_obj` (a blind/dark-room witness, or
    one without detect-invis, sees "something"). Each line verified against its
    exact ROM `act()` format string: acid/fire effect, bless object,
    enchant_armor, enchant_weapon (TO_ROOM leg preserves ROM's `"explodeds!"`
    typo), fireproof, recharge, remove_curse object + per-item `$n's $p` loop,
    pick-lock, portal/nexus. Caster `_send_to_char` legs left baked (the caster
    always sees a visible target).
  - **Filed (not fixed):** MAGIC-010 (object-invis `$p` masks caster+room — the
    object is genuinely ITEM_INVIS at render time; behaviorally distinct, flips
    ~3 pinned baked-name test assertions). Corrected the stale MAGIC-005 row
    (text is already ROM-correct; only the same object-`$p` masking remains).
  - **Tests**: `tests/integration/test_magic007_object_pers_masking.py` (2).
    Full suite: 5213 passed, 4 skipped.
  - Commit: `84c9e4a0` (unpushed).

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_MAGIC007_OBJECT_PERS_MASKING.md](SESSION_SUMMARY_2026-06-01_MAGIC007_OBJECT_PERS_MASKING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.31 |
| Tests | full suite: 5213 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | MAGIC-004/005/006/009/010 + FIGHT-035/036; CAST-009 + TRAIN-005 remain (MAGIC-007 + MAGIC-008 closed) |

## Next Intended Task

Continue the INV-025 / INV-027 PERS-masking pass via the filed gaps, in order:

1. **MAGIC-010** — object-invis `$p` masks caster + room (both legs). Render the
   caster leg via `act_format(recipient=caster, actor=caster, arg1=obj)` and the
   room leg via `act_to_room`; update the ~3 pinned baked-name assertions
   (`test_skills_buffs.py:584/585/618/619`,
   `test_act_cap_002_room_broadcast.py:123`) to "Something fades out of sight."
2. **MAGIC-005** — poison-object room legs (infused/coated) → `act_to_room`
   with `$p` (text already correct; only masking remains).
3. **MAGIC-006 / FIGHT-036** — `their`→`$s` pronoun (+ dirt-kick colour).
4. **MAGIC-004** (chain_lightning) and **FIGHT-035** (disarm) — structural
   TO_VICT/TO_NOTVICT splits to rebuild, not token swaps.

`CAST-009` (failed-cast skill improvement) also remains 🔄 OPEN in
`MAGIC_C_AUDIT.md`.
