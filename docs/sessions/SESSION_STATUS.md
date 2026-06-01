# Session Status — 2026-06-01 — INV-025 single-actor spell PERS masking + invis order (2.12.30)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.30)**:
  - **INV-025 / INV-027 — single-actor spell-effect PERS masking sweep.**
    Converted 26 single-actor `act("$n ...", TO_ROOM)` sites in
    `mud/skills/handlers.py` from the module-level `_act_room` (baked
    `_character_name()`, no `can_see` check) to the shared `act_to_room` helper
    (per-recipient PERS masking + per-NPC `TRIG_ACT`). Covers floating disc,
    gate ×4, summon/teleport/nexus/word-of-recall travel, infravision, invis,
    mass-invis fade, change-sex `$mself`, pink outline, purple smoke, word of
    divine power, blinding ray `$s`, poison/blindness saves, calm "looks more
    relaxed". Each line verified against its exact ROM `act()` format string.
  - **MAGIC-008 — `invis` broadcast order.** Reordered `spell_invisibility`
    to broadcast the fade-out room line **before** applying `AFF_INVISIBLE`
    (`src/magic.c:3650-3659`), so the still-visible actor renders by name;
    `mass_invis` already broadcast first. Exposed by the masking sweep.
  - **Filed (not fixed):** MAGIC-004 (chain_lightning split), MAGIC-005
    (poison_weapon text/subject), MAGIC-006 (plague `their`→`$s`), MAGIC-007
    (object-`$p` sweep remainder), FIGHT-035 (disarm double-broadcast),
    FIGHT-036 (dirt-kick colour/`$s`).
  - **Tests**: `tests/integration/test_inv025_spell_self_effect_pers_masking.py`
    (5). Full suite: 5211 passed, 4 skipped.
  - Also committed the prior session's uncommitted 2.12.29 work
    (cancellation + portal PERS masking, shared `act_to_room`) as `24ef1759`.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_INV025_SINGLE_ACTOR_SPELL_PERS_MASKING.md](SESSION_SUMMARY_2026-06-01_INV025_SINGLE_ACTOR_SPELL_PERS_MASKING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.30 |
| Tests | full suite: 5211 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | MAGIC-004/005/006/007/009 + FIGHT-035/036 (this session); MAGIC-008 closed; CAST-009 + TRAIN-005 remain |

## Next Intended Task

Continue the INV-025 / INV-027 PERS-masking pass via the filed gaps:

1. **MAGIC-007** — object-`$p` sweep remainder (acid/fire inventory-burn,
   object-invis `$p fades out of sight`, portal/nexus `$p rises`, pick-lock
   `$n picks the lock on $p`, enchant glows). Same invariant as the single-actor
   sweep, mechanical once each ROM `act()` format string + `arg1=obj` is verified.
   Then audit the `message`-variable `_act_room` sites (`handlers.py` ~1566/1599/
   3627/3774/4444/6537/6599/7133) for baked names.
2. **MAGIC-004** (chain_lightning) and **FIGHT-035** (disarm) — structural
   divergences requiring ROM's TO_VICT/TO_NOTVICT splits rebuilt, not token swaps.
3. **MAGIC-006 / FIGHT-036** — `their`→`$s` pronoun + (dirt-kick) `{5..{x` colour.

`CAST-009` (failed-cast skill improvement) also remains 🔄 OPEN in
`MAGIC_C_AUDIT.md`.
