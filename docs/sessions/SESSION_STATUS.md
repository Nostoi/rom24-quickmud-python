# Session Status — 2026-05-30 — FIGHT-032/033/034 + VISION-002

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows). Today closed **FIGHT-032** (defense PERS
  masking), **FIGHT-033** (frost/shocking weapon name), **FIGHT-034** (auto-split
  PERS+cap), and **VISION-002** (dark-gate same-room divergence).
- **Last completed** (this session):
  - **`FIGHT-032` (defense PERS masking) ✅ FIXED (2.11.44)**
    — `check_parry`/`check_shield_block`/`check_dodge` now route attacker and
    defender names through `pers()` per ROM `act()` PERS substitution.
    7-assertion test; no re-baselines.
  - **`FIGHT-033` (frost/shocking victim TO_CHAR weapon name) ✅ FIXED (2.11.45)**
    — WEAPON_FROST/SHOCKING TO_CHAR templates now include `{weapon_name}`.
    2-assertion test; re-baselined 2 stale unit assertions.
  - **`FIGHT-034` (auto-split PERS + capitalize) ✅ FIXED (2.11.46)**
    — Both `_auto_split` and `do_split` route per-recipient messages through
    `pers(actor, member)` + `capitalize_act_line`. 5-assertion test.
  - **`VISION-002` (dark-gate same-room divergence) ✅ FIXED (2.11.47)**
    — Removed `observer_room is target_room` conjunction from dark gate in
    `can_see_character`. ROM checks `room_is_dark(ch->in_room)` unconditionally;
    Python now matches. 5-assertion test.
- **Earlier today**: ACT-CAP-001 (2.11.40), FIGHT-031 (2.11.39), INV-029 (2.11.38),
  ACT-CAP-002 (2.11.41), ACT-CAP-003/004 (2.11.42/2.11.43).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-30_FIGHT-032_033_034_VISION-002.md](SESSION_SUMMARY_2026-05-30_FIGHT-032_033_034_VISION-002.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.47 |
| Tests | ~5045 passed, 4 skipped, 0 failed (full parallel suite; +5 VISION-002, +7 FIGHT-032, +2 FIGHT-033, +5 FIGHT-034) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants — all known gaps closed; next: new INV probes |

## Next Intended Task

All FIGHT.c audit gaps and HANDLER.c VISION divergences are closed. The per-file
audit tracker has no remaining ⚠️ Partial / ❌ Not Audited rows. Cross-file
invariants (INV-027, INV-029) are fully enforced. Per AGENTS.md, the next phase
is **cross-file invariants as primary pass**: pick a candidate contract not yet
covered by an INV row (affect ticks, position transitions, mob script triggers,
group/follower chain), run a 5-minute ROM C → Python probe, then either close as
a gap or file as INV-NNN.

Carried-open: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); pet-shop haggle / "now follows you"
wrong-channel (INV-001 family); `Character.pet` stale type annotation; `do_cast`
object-targeting legs; unused imports in `group_commands.py`.

## Commit / push state

- All changes committed on `master` (4 parity commits ahead of FIGHT-031 session).
- **Local-only, NOT pushed** — await user's say-so before pushing to `origin/master`.