# Session Status — 2026-05-29 — FIGHT-029 fixed (do_rescue SINGLE-DELIVERY)

## Current State

- **Active mode**: cross-file invariants (the per-file audit tracker is
  exhausted). This session closed **FIGHT-029**, the last OPEN INV-001
  SINGLE-DELIVERY violation from the MAGIC-003 handoff, and filed two new
  siblings (FIGHT-030 + INV-001 (d)) while doing so.
- **Last completed** (this session):
  - **`FIGHT-029`** ✅ FIXED (master 2.11.25, `da73d821`) — `do_rescue` is void
    in ROM (`src/fight.c:3089-3091`); `rescue()` now delivers all three legs
    (TO_CHAR/TO_VICT/TO_NOTVICT) via the canonical `_send_to_char` channel and
    `do_rescue` returns `""` (fail-path mailbox append also dropped). Fixes the
    rescuer double-delivery (kill/surrender shape) AND the victim/room
    wrong-channel (MAGIC-003 shape). Test
    `tests/integration/test_rescue_single_delivery.py` splits the shape
    (count-once for the rescuer + push-present/mailbox-empty for victim+bystander,
    per the advisor catch that a pure count test false-greens on the vict/room
    legs).
  - **Filed `FIGHT-030`** (🔄 OPEN, `FIGHT_C_AUDIT.md`) — `do_rescue` omits
    ROM's `check_killer(ch, fch)` (`src/fight.c:3097`), so a PC rescuing an ally
    fighting **another PC** escapes the `PLR_KILLER` flag. Surfaced by the
    advisor on the full `do_rescue` read. Not folded into FIGHT-029.
  - **Filed `INV-001 (d)`** (🔄 OPEN, `CROSS_FILE_INVARIANTS_TRACKER.md`) — the
    `"You are still recovering."` wait-state guard double-delivers (append +
    return) across 7 `combat.py` commands + `skills/registry.py`. Not a ROM
    line. One-sweep cleanup.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_FIGHT_029_RESCUE_SINGLE_DELIVERY.md](SESSION_SUMMARY_2026-05-29_FIGHT_029_RESCUE_SINGLE_DELIVERY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.25 |
| Tests | 4974 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | INV-001 SINGLE-DELIVERY family (FIGHT-030 + INV-001 (d) open) + cross-file invariants |

## Next Intended Task

Close **`FIGHT-030`** (`FIGHT_C_AUDIT.md`) — `rom-gap-closer FIGHT-030`. Add
`check_killer(caster, foe)` in `mud/skills/handlers.py:rescue` between the
`stop_fighting` and `set_fighting` pairs (ROM ordering, `src/fight.c:3097`);
test asserts the rescuer gains `PlayerFlag.KILLER` when rescuing an ally
fighting another non-clan/non-killer PC. Stays in the `do_rescue` context.

After that, the **INV-001 (d) "still recovering" sweep** is a small one-commit
cross-command cleanup (drop the `char.messages.append` in ~8 sites; locate via
`grep "still recovering" mud/`). Beyond those, the per-file audit tracker is
exhausted — cross-file invariants (`CROSS_FILE_INVARIANTS_TRACKER.md`) is the
standing pass; the return-value-plus-mailbox (`do_rescue`/`do_surrender`/
`do_kill`) shape keeps surfacing INV-001 siblings, so a targeted sweep for that
pattern is high-yield.
