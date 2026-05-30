# Session Status — 2026-05-30 — FIGHT-032/033 Defense PERS + Weapon Name

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows). Today closed **FIGHT-032** (defense
  TO_CHAR/TO_VICT PERS masking) and **FIGHT-033** (frost/shocking victim TO_CHAR
  `$p` weapon name).
- **Last completed** (this leg):
  - **`FIGHT-032` (defense PERS masking) ✅ FIXED (2.11.44)**
    — `check_parry`/`check_shield_block`/`check_dodge` now route attacker and
    defender names through `pers()` per ROM `act()` PERS substitution.
    7-assertion test; no re-baselines.
  - **`FIGHT-033` (frost/shocking victim TO_CHAR weapon name) ✅ FIXED (2.11.45)**
    — WEAPON_FROST TO_CHAR: `"The cold touch of {weapon_name} surrounds you
    with ice."` (was `"The cold touch surrounds you with ice."` missing `$p`).
    WEAPON_SHOCKING TO_CHAR: `"You are shocked by {weapon_name}."` (was
    `"You are shocked by the weapon."` — generic instead of `$p`).
    2-assertion test; re-baselined 2 stale unit assertions.
- **Earlier today**: ACT-CAP-001 (2.11.40), FIGHT-031 (2.11.39), INV-029 (2.11.38),
  ACT-CAP-002 (2.11.41), ACT-CAP-003/004 (2.11.42/2.11.43).
- **Pointer to latest summary**: Will be written on session end.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.45 |
| Tests | ~5039 passed, 4 skipped, 0 failed (full parallel suite; +7 FIGHT-032, +2 FIGHT-033) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants — FIGHT-032/033 closed; remaining: FIGHT-034, VISION-002 |

## Next Intended Task

FIGHT-032/033 are closed. Remaining FIGHT.c audit gaps:

1. **`FIGHT-034`** — auto-split per-member line not capitalized + bypasses PERS.
   ROM `do_split` (`src/act_comm.c`) delivers `act("$n splits %d silver coins.
   Your share is %d silver.", ch, NULL, gch, TO_VICT)` — `$n` resolves
   through PERS and act_new caps the first letter. Python `_auto_split`
   builds a fixed string. Two divergences: INV-029 cap + INV-027 PERS mask.
2. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`). Larger scope; failing test first.

Carried-open: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); pet-shop haggle / "now follows you"
wrong-channel (INV-001 family); `Character.pet` stale type annotation; `do_cast`
object-targeting legs.

## Commit / push state

- All changes committed on `master` (3 commits ahead of origin).
- **Local-only, NOT pushed** — await user's say-so before pushing to `origin/master`.