# Session Status — 2026-05-29 — CAST-003 + MAGIC-003 fixed (MAGIC-002 family complete)

## Current State

- **Active mode**: the MAGIC-002 affect-message family is now **complete** —
  armor (2.11.20), bless (2.11.21), CAST-002 (2.11.22), and this session's
  **CAST-003** (2.11.23) + **MAGIC-003** (2.11.24). The per-file audit tracker
  is exhausted; cross-file invariants remains the standing pass.
- **Last completed** (this session):
  - **`CAST-003`** ✅ FIXED (master 2.11.23, `6551a743`) — `do_cast`'s offensive
    object/char no-fight branch now returns ROM's distinct
    `"Cast the spell on whom or what?"` (`src/magic.c:471`, for `curse`/`poison`)
    instead of `TAR_CHAR_OFFENSIVE`'s `"Cast the spell on whom?"` (`:376`).
    Guard test tightened to assert the exact wording.
  - **`MAGIC-003`** ✅ FIXED (master 2.11.24, `95a6d776`) — `shield`/`sanctuary`/
    `blindness`/`weaken` now deliver their victim + room-broadcast lines via the
    canonical single-delivery channel (`_send_to_char`/`push_message`), not the
    raw `char.messages.append` mailbox (INV-001 family). Connected-PC delivery
    test added (`tests/integration/test_magic_003_affect_message_channel.py`);
    the mailbox fallback for disconnected/test chars is preserved.
  - **Filed `FIGHT-029`** (🔄 OPEN, `7d602d2f`) — `do_rescue` SINGLE-DELIVERY
    violation: `rescue()` appends the rescuer line to `caster.messages` AND
    `do_rescue` returns it, so a connected PC gets "You rescue X!" twice (the
    `do_kill`/`do_surrender` shape); victim/room legs also wrong-channel.
    Surfaced by the advisor while closing MAGIC-003; filed in `FIGHT_C_AUDIT.md`
    + INV-001 cross-ref, **not** folded into MAGIC-003.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_MAGIC_003_AFFECT_CHANNEL.md](SESSION_SUMMARY_2026-05-29_MAGIC_003_AFFECT_CHANNEL.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.24 |
| Tests | 4973 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | INV-001 SINGLE-DELIVERY family (FIGHT-029 open) + cross-file invariants |

## Next Intended Task

Close **`FIGHT-029`** (`FIGHT_C_AUDIT.md`) — `rom-gap-closer FIGHT-029`. The
`do_rescue` SINGLE-DELIVERY fix: have `do_rescue` `return ""` (discard the
return like `do_kill`/`do_surrender`) and migrate `rescue`'s three legs
(`mud/skills/handlers.py:7081-7091`) from `char.messages.append` onto
`_push_message`/`_send_to_char` (self via push, room via the per-occupant
`_send_to_char` loop). Needs a connection-loop double-delivery test (template
`tests/integration/test_kill_command_single_delivery.py` /
`test_surrender_single_delivery.py`). Keeps the work in the INV-001 family.

Beyond that, the per-file audit tracker is exhausted — cross-file invariants
(`CROSS_FILE_INVARIANTS_TRACKER.md`) is the standing pass (candidate areas:
affect ticks, position transitions, mob script triggers, group/follower chain).
A targeted sweep for other return-value-plus-mailbox commands (the `do_rescue`
shape) would likely surface more INV-001 siblings.
