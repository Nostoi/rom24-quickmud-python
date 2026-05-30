# Session Status — 2026-05-30 — FIGHT-032 Defense PERS Masking

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows). Today closed **FIGHT-032** (defense
  TO_CHAR/TO_VICT PERS masking — parry/shield_block/dodge route names through
  `pers()` per recipient instead of raw `getattr(x, "name")`).
- **Last completed** (this leg):
  - **`FIGHT-032` (defense PERS masking) ✅ FIXED (2.11.44)**
    — `check_parry`/`check_shield_block`/`check_dodge` now route attacker and
    defender names through `pers()` per ROM `act()` PERS substitution:
    invisible actors render as "someone", NPCs render `short_descr`.
    7-assertion test; no re-baselines (existing assertions use visible PCs
    where `pers()` returns `name` unchanged).
- **Earlier today**: ACT-CAP-001 (2.11.40), FIGHT-031 (2.11.39), INV-029 (2.11.38),
  ACT-CAP-002 (2.11.41), ACT-CAP-003/004 (2.11.42/2.11.43).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-30_FIGHT-032_DEFENSE_PERS_MASKING.md](SESSION_SUMMARY_2026-05-30_FIGHT-032_DEFENSE_PERS_MASKING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.44 |
| Tests | 5037 passed, 4 skipped, 0 failed (full parallel suite; +7 FIGHT-032 tests) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants — FIGHT-032 closed; remaining: FIGHT-033/034, VISION-002 |

## Next Intended Task

FIGHT-032 is closed. The remaining FIGHT.c audit gaps:

1. **`FIGHT-033`** — WEAPON_FROST and WEAPON_SHOCKING victim lines drop the
   `$p` weapon name. Text-content divergence (the FIGHT-031 capitalization
   fix left these uncapped because they already lead with a capital letter,
   but they also miss the `$p` weapon short_descr).
2. **`FIGHT-034`** — auto-split per-member line not capitalized + bypasses PERS.
3. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`). Larger scope; failing test first.

Carried-open: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); pet-shop haggle / "now follows you"
wrong-channel (INV-001 family); `Character.pet` stale type annotation; `do_cast`
object-targeting legs.

## Commit / push state

- All changes on `master` (committed as `e09b9119` for ACT-CAP-003/004, pending
  FIGHT-032 commit).