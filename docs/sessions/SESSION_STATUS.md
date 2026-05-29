# Session Status — 2026-05-29 — WIZ-046 (do_violate wizinvis gate) + INV-027 probe

## Current State

- **Active mode**: cross-file invariants (the per-file audit tracker is
  exhausted — no ⚠️ Partial / ❌ Not Audited rows). This session closed the
  ready WIZ-046 gap, then probed the INV-027 candidate to a definitive
  outcome (violation confirmed, enforcement reverted, blocker pinned).
- **Last completed** (this session):
  - **`WIZ-046`** ✅ FIXED (master 2.11.31, `dfbb17f5`) — ROM `do_violate`
    (`src/act_wiz.c:1026-1051`) is the structural twin of `do_goto`: it sends each
    bamfout/bamfin (or default swirling-mist) line via `act(..., rch, TO_VICT)`
    **only** to occupants where `get_trust(rch) >= ch->invis_level`. Python's
    `do_violate` (`mud/commands/imm_server.py:163`) routed its four bamf
    broadcasts through the ungated `_act_room`, leaking a wiz-invis immortal's
    presence to every witness. Now reuses the WIZ-045 `_act_room_invis_gated`
    helper (import swapped). Tests:
    `tests/integration/test_act_wiz_command_parity.py::test_violate_suppresses_bamf_for_subtrust_witnesses_when_wizinvis`
    (both legs) + `::test_violate_bamf_visible_to_all_when_not_wizinvis`.
  - **`INV-027` (ACT-PERS-NAME-MASKING)** PROBED (master 2.11.32, `47449114`) —
    violation **confirmed** (`mud/utils/act.py:act_format._pers` lacks the ROM
    `PERS`→`can_see` gate; ROM contract holds for `act(TO_ROOM)` and wiznet alike,
    `src/merc.h:2145` / `src/handler.c:2618-2664` / `src/act_wiz.c:188`).
    Enforcement **attempted and reverted**: routing `_pers` through
    `can_see_character` regressed 15 tests including real production wiznet paths,
    because `announce_wiznet_new_player` (`mud/net/connection.py:207`) passes a
    **roomless** `SimpleNamespace` placeholder and `can_see_character`
    (`mud/world/vision.py:161-164`) bails `room is None → False` (ROM `can_see`
    has no `victim->in_room` check). Contract **locked** as a strict `xfail` in
    `tests/integration/test_inv027_act_pers_name_masking.py`; INV-027 stays OPEN.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_WIZ_046_AND_INV_027_PROBE.md](SESSION_SUMMARY_2026-05-29_WIZ_046_AND_INV_027_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.32 |
| Tests | 4985 passed, 4 skipped, 1 xfailed (full suite) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | Cross-file invariants (INV-027 OPEN — blocked on a `can_see_character` room-None reconciliation) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **INV-027 prerequisite — roomless-actor visibility (verify ordering first, then
   choose).** Surfaced this session. **Do not assume the fix is "reorder
   `can_see_character`"** — the decision is three-way and ordering-dependent:
   (a) reorder `can_see_character` (`mud/world/vision.py:161-164`) to ROM `can_see`
   ordering (trust/incog/holylight before the dark gate; no `victim->in_room`
   bail — `src/handler.c:2618-2664`); (b) move room-placement before the wiznet
   announce; (c) bake the name for the synthetic newbie/login cases. **Confirm the
   announce/placement ordering BEFORE picking** — `announce_wiznet_new_player`
   takes `name: str` and builds its `SimpleNamespace` placeholder internally,
   firing at `mud/net/connection.py:1698` **before** `char.room` is set at `:1879`,
   so "pass the real char" does not cleanly work and fixing `can_see_character`
   alone would leave "Newbie alert! someone sighted." still broken. Note also that
   `can_see_character`'s room-None branch guards a state ROM never reaches, so
   "reconciling" it is a design choice, not strictly a bug fix. Give the chosen fix
   a gap ID (a `VISION-00x` row is worth considering so it's `rom-gap-closer`-able),
   write the ROM-contract failing test, run `gitnexus_impact` (43 `act_format`
   callers + combat use the helper — expect CRITICAL). **This unblocks INV-027.**
2. **INV-027 enforcement** — after #1: route `act_format._pers` through the
   reconciled visibility check, remove the `xfail` marker, and upgrade the
   `SimpleNamespace` mocks in `test_wiznet`/`test_spec_funs` to room/`has_affect`
   bearing. Promote the per-recipient subset to ENFORCED (broadcast-once stays
   MESSAGE_DELIVERY-divergent).
3. Fresh cross-file probe in an area not yet covered by an INV row (affect ticks,
   position transitions, mob script triggers, group/follower chain).

Carried-open items (see the summary's Outstanding): pet-shop haggle/"now follows
you" wrong-channel (INV-001 family, mailbox-only); `Character.pet` stale type
annotation; `do_cast` object-targeting legs; converter hardening; the
`test_backstab_uses_position_and_weapon` / `test_combat_death.py` xdist flakes.
