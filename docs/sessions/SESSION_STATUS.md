# Session Status — 2026-05-30 — ACT-CAP-003/004 Communication + Channel Capitalization

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows). Today closed **ACT-CAP-003** (do_say/do_tell/
  do_shout/do_yell/do_emote capitalization) and **ACT-CAP-004** (broadcast_global
  channel callers capitalization), the final two INV-029 cousin surfaces.
- **Last completed** (this leg):
  - **`ACT-CAP-003` (communication command capitalization) ✅ FIXED (2.11.42)**
    — `capitalize_act_line` applied to 6 output sites across 5 functions in
    `mud/commands/communication.py`. 6-assertion test; 4 re-baselines.
  - **`ACT-CAP-004` (broadcast_global channel capitalization) ✅ FIXED (2.11.43)**
    — `capitalize_act_line` applied to 9 channel callers (auction, gossip, grats,
    quote, question, answer, music, clan, immtalk). Weather path correctly
    uncapped (ROM uses `send_to_char`). 6-assertion test.
- **INV-029 status**: FULLY ENFORCED across all delivery surfaces (`act_format`,
  `imm_commands` PERS-f-strings, combat `render_for`/`_broadcast_pos_change`,
  `broadcast_room`, `Room.broadcast`/`_message_room`, TO_ALL caster legs,
  do_say/tell/shout/yell/emote, broadcast_global channels). Only `broadcast_global`
  weather remains uncapped (correct — ROM `send_to_char`).
- **Earlier today**: ACT-CAP-001 (2.11.40), FIGHT-031 (2.11.39), INV-029 (2.11.38),
  ACT-CAP-002 (2.11.41).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-30_ACT-CAP-003_004_COMMUNICATION_CHANNEL_CAPITALIZE.md](SESSION_SUMMARY_2026-05-30_ACT-CAP-003_004_COMMUNICATION_CHANNEL_CAPITALIZE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.43 |
| Tests | 5030 passed, 4 skipped, 0 failed (full parallel suite; +12 ACT-CAP-003/004 tests) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants — INV-029 fully enforced; remaining open items are FIGHT-032/033/034 and VISION-002 |

## Next Intended Task

INV-029 (`act_new` first-letter-cap) is now **fully enforced**. The remaining
cross-file work is no longer capitalization-related. Concrete next options:

1. **`FIGHT-032`** — defense TO_CHAR/TO_VICT lines bypass PERS (raw `name`);
   route `check_parry`/`check_dodge`/`check_shield_block` through `pers()`.
2. **`FIGHT-033`** — WEAPON_FROST and WEAPON_SHOCKING victim lines drop the
   `$p` weapon name.
3. **`FIGHT-034`** — auto-split per-member line not capitalized + bypasses PERS.
4. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`). Larger scope; failing test first.

Carried-open: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); pet-shop haggle / "now follows you"
wrong-channel (INV-001 family); `Character.pet` stale type annotation; `do_cast`
object-targeting legs.

## Commit / push state

- All changes on branch `feat/act-cap-002` (branched from `master` at `b20a73e0`).
- **Local-only, NOT pushed** — await the user's say-so before pushing to
  `origin/master`.