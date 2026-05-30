# Session Status — 2026-05-29 — WIZ-047 FIXED (INV-027 PERS contract — `_act_room` half)

## Current State

- **Active mode**: cross-file invariants (the per-file audit tracker is
  exhausted — no ⚠️ Partial / ❌ Not Audited rows). This session closed
  **WIZ-047** (the remaining `imm_commands._act_room` half of INV-027) and filed
  the one sibling leak that surfaced (**WIZ-048**) durably as OPEN.
- **Last completed** (this session):
  - **`WIZ-047`** ✅ FIXED (master 2.11.35, `d7f88228`) —
    `mud/commands/imm_commands.py:_act_room` now renders `$n` per-recipient via
    `mud/world/vision.py:pers(char, person)`, mirroring ROM `do_transfer`'s
    `act(..., TO_ROOM)` PERS masking (`src/act_wiz.c:870,873`). An invisible /
    wiz-invis transferred immortal's name is masked to `"someone"` for
    non-seeing witnesses (line still delivered; actor skipped). `gitnexus_impact`
    = LOW (do_transfer d=1, do_teleport d=2). Test:
    `tests/integration/test_wiz047_transfer_pers_name_masking.py` (2). This is
    the remaining `_act_room` half of the INV-027 (ACT-PERS-NAME-MASKING)
    contract; the `act_format._pers` half was enforced in 2.11.34.
  - **`WIZ-048`** ❌ FILED OPEN (master 2.11.35 doc, `d7f88228`) — `do_transfer`'s
    `"$n has transferred you."` (ROM `src/act_wiz.c:874-875`, TO_VICT, `$n` = the
    immortal) is sent with the immortal's real name unconditionally
    (`imm_commands.py:282-285`), leaking a wiz-invis immortal's identity to the
    transferred victim. ROM masks via `PERS(ch, victim)`. Same INV-027 contract,
    different line than WIZ-047. Surfaced while closing WIZ-047. Filed in
    `ACT_WIZ_C_AUDIT.md` (Phase 3) + cross-ref'd from INV-027.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_WIZ-047_FIXED.md](SESSION_SUMMARY_2026-05-29_WIZ-047_FIXED.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.35 |
| Tests | 4991 passed, 4 skipped, 0 failed (full parallel suite, ~124s, on the committed tree); includes the 2 new WIZ-047 tests |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | Cross-file invariants (INV-027: WIZ-047 FIXED; WIZ-048 + VISION-002 OPEN) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **`WIZ-048`** — the remaining INV-027 PERS leak. `do_transfer`'s
   `"$n has transferred you."` (`imm_commands.py:282-285`, ROM
   `src/act_wiz.c:874-875`) renders the immortal's name unconditionally;
   `rom-gap-closer`-able: failing per-recipient test (victim without
   detect-invis → "someone has transferred you."; with detect-invis → name),
   then route through `mud/world/vision.py:pers(char, victim)`. One gap = one
   test = one commit. With WIZ-047 + WIZ-048 both closed, the INV-027 PERS
   contract is fully enforced across `act_format`, the imm `_act_room` TO_ROOM
   path, and the `do_transfer` TO_VICT path.
2. **`VISION-002`** — the dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`: ROM masks on `room_is_dark(ch->in_room)` with no
   same-room guard). Larger scope (could shift cross-room/scan visibility); write
   a failing test first. Filed in `HANDLER_C_AUDIT.md`.
3. Fresh cross-file probe in an area not yet covered by an INV row (affect ticks,
   position transitions, mob script triggers, group/follower chain).

Carried-open items (see the summary's Outstanding section): known **xdist
flakes** (`test_combat_death.py`, `test_backstab_uses_position_and_weapon` —
documented carried-open; pass in isolation, can flake under some parallel worker
groupings; this session's full run had **zero** failures); pet-shop
haggle/"now follows you" wrong-channel
(INV-001 family, mailbox-only); `Character.pet` stale type annotation; `do_cast`
object-targeting legs; converter hardening. Non-blocking (ROM-faithful, not a
gap): `_pers`/`_act_room`→`can_see_character` consumes an RNG draw on the sneak
branch (most reachable via a sneaking player moving) — findability note only, in
case a future seeded `act_format`/`_act_room`-downstream assertion flakes.

> Tooling note: the Bash/Read/MCP/advisor output channels buffered intermittently
> this session (calls returning empty, then recovering — same mode as the
> INV-027-prereq session). Worked around via temp-file routing + `python3`
> prints. All "passing"/"FIXED" claims here were read from rendered output, not
> assumed.
