# Session Status — 2026-05-29 — VISION-001 prerequisite + INV-027 ENFORCED

## Current State

- **Active mode**: cross-file invariants (the per-file audit tracker is
  exhausted — no ⚠️ Partial / ❌ Not Audited rows). This session closed the
  INV-027 prerequisite (VISION-001), carried INV-027 through to ENFORCED, and
  filed the one sibling leak that surfaced (WIZ-047) durably as OPEN.
- **Last completed** (this session):
  - **`VISION-001`** ✅ FIXED (master 2.11.33, `8270c544`) — dropped the non-ROM
    `target_room is None` bail in `can_see_character` (`mud/world/vision.py`). ROM
    `can_see` (`src/handler.c:2618-2664`) never checks `victim->in_room`. A
    28-direct-caller census (CRITICAL blast radius) confirmed no
    descriptor/registry/`room.people` iterator observes a roomless target except
    the intentional synthetic wiznet subjects. Test:
    `tests/test_vision_roomless_target.py`. Deferred sibling VISION-002 (dark-gate
    same-room divergence) filed OPEN.
  - **`INV-027` (ACT-PERS-NAME-MASKING)** ✅ ENFORCED, per-recipient `act_format`
    subset (master 2.11.34, `e1829bdf`) — `mud/utils/act.py:_pers` now routes
    `$n`/`$N` through `can_see_character` (gated on a concrete `viewer`);
    `announce_wiznet_new_player` builds a real roomless `Character` subject; the
    15 predicted regressions were under-specified test mocks, enriched to
    roomed/`has_affect`-bearing doubles with expected strings unchanged. The
    `xfail` in `test_inv027_act_pers_name_masking.py` is removed (now passing).
    The `recipient=None` broadcast-once path stays the MESSAGE_DELIVERY.md
    divergence (boundary test pins it).
  - **`WIZ-047`** ❌ FILED OPEN (master 2.11.34 doc, `1089dd13`) —
    `imm_commands._act_room` still does unconditional `$n` replacement (no PERS
    masking), so `do_transfer` leaks an invisible/wiz-invis immortal's name. The
    remaining half of the INV-027 PERS contract; the enforcement scoped its code
    fix to `act_format._pers`. Filed in `ACT_WIZ_C_AUDIT.md` (Phase 3), cross-ref'd
    from INV-027.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_VISION_001_AND_INV_027_ENFORCED.md](SESSION_SUMMARY_2026-05-29_VISION_001_AND_INV_027_ENFORCED.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.34 |
| Tests | 4989 passed, 4 skipped, 0 xfailed (full suite) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | Cross-file invariants (INV-027 ENFORCED; WIZ-047 + VISION-002 OPEN) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **`WIZ-047`** — the remaining half of the INV-027 PERS contract.
   `imm_commands._act_room` (`mud/commands/imm_commands.py:475`) renders `$n`
   unconditionally; `do_transfer`'s arrival/departure announce leaks an
   invisible/wiz-invis immortal's name. `rom-gap-closer`-able: failing
   per-recipient test (non-seeing witness → "someone", seeing witness → name),
   then route `$n` through `mud/world/vision.py:pers(char, person)` per recipient.
   One gap = one test = one commit.
2. **`VISION-002`** — the dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`: ROM masks on `room_is_dark(ch->in_room)` with no
   same-room guard). Larger scope (could shift cross-room/scan visibility); write
   a failing test first. Filed in `HANDLER_C_AUDIT.md`.
3. Fresh cross-file probe in an area not yet covered by an INV row (affect ticks,
   position transitions, mob script triggers, group/follower chain).

Carried-open items (see the summary's Next Steps): pet-shop haggle/"now follows
you" wrong-channel (INV-001 family, mailbox-only); `Character.pet` stale type
annotation; `do_cast` object-targeting legs; converter hardening; the
`test_backstab_uses_position_and_weapon` / `test_combat_death.py` xdist flakes.
Non-blocking (ROM-faithful, not a gap): `_pers`→`can_see_character` now consumes
an RNG draw on the sneak branch (most reachable via a sneaking player moving) —
findability note only, in case a future seeded `act_format`-downstream assertion flakes.
