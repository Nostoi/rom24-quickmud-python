# Session Status — 2026-05-29 — FIGHT-030 + INV-001 (d) fixed (INV-001 family ENFORCED)

## Current State

- **Active mode**: cross-file invariants (the per-file audit tracker is
  exhausted). This session closed the two remaining open members of the
  **INV-001 SINGLE-DELIVERY** family that surfaced from the `do_rescue` read
  during FIGHT-029. **INV-001 is now fully ✅ ENFORCED — no open violations.**
- **Last completed** (this session):
  - **`FIGHT-030`** ✅ FIXED (master 2.11.26, `095e268a`) — `do_rescue` now
    calls `check_killer(caster, foe)` between the `stop_fighting` and
    `set_fighting` pairs (`src/fight.c:3094-3099`), so a clan PC rescuing an ally
    from **another PC** is flagged `PlayerFlag.KILLER` as ROM does. Placement is
    load-bearing (`check_killer` early-returns once `attacker.fighting is foe`,
    `engine.py:1291`). Test `tests/integration/test_rescue_killer_flag.py`
    (PC-foe flags; NPC-foe doesn't).
  - **`INV-001 (d)`** ✅ FIXED (master 2.11.27, `0956f8cf`) — the
    `"You are still recovering."` wait-state guard double-delivered across 7
    `combat.py` commands (`do_kick`, `do_rescue`, `do_backstab`, `do_bash`,
    `do_berserk`, `do_flee`, `do_cast`): `char.messages.append(...)` AND
    `return ...`. Dropped the append, kept the return.
    `mud/skills/registry.py:163` deliberately EXCLUDED (raises not returns, no
    production callers — single mailbox delivery, not a double; documented in
    the tracker so it isn't re-flagged). Test
    `tests/integration/test_still_recovering_single_delivery.py` (grep-guard on
    all 7 sites + behavioral single-delivery through `do_kick`).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_FIGHT_030_AND_STILL_RECOVERING_SWEEP.md](SESSION_SUMMARY_2026-05-29_FIGHT_030_AND_STILL_RECOVERING_SWEEP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.27 |
| Tests | 4978 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | Cross-file invariants (INV-001 SINGLE-DELIVERY now fully ENFORCED) |

## Next Intended Task

The INV-001 SINGLE-DELIVERY family is fully ✅ ENFORCED, so that high-yield vein
is exhausted. Cross-file invariants remains the standing pass (per-file audit
tracker has no ⚠️ Partial / ❌ Not Audited rows). Concrete next options:

1. **`SHOP-PET-002`** (open, `FIGHT_C_AUDIT.md`) — `rom-gap-closer SHOP-PET-002`.
   Pet purchase should `create_mobile(pIndexData)` (fresh re-roll) rather than
   clone the template. Local single-function divergence.
2. **Fresh cross-file invariant probe** — pick a candidate area not yet covered
   by an INV row (affect ticks, position transitions, mob script triggers,
   group/follower chain), run the 5-minute probe-then-scope (read ROM C contract
   → read Python equivalent → one failing test), then close as a gap or file the
   next free INV-NNN. See AGENTS.md "Cross-File Invariants".

Other carried-open items (see the summary's Outstanding section): `do_cast`
object-targeting legs, converter hardening (`convert_skills_to_json.py` lossy),
and two known xdist flakes (`test_backstab_uses_position_and_weapon`,
`test_combat_death.py`).
