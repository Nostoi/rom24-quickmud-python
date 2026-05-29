# Session Status — 2026-05-29 — WIZ-045 (do_goto wizinvis bamf-announce gate) + INV-027 correction

## Current State

- **Active mode**: cross-file invariants (the per-file audit tracker is
  exhausted — no ⚠️ Partial / ❌ Not Audited rows). This session probed the
  **INV-027 candidate** and, in doing so, **disproved its documented ROM
  mechanism**, then closed the real per-command gap it pointed at (`WIZ-045`).
- **Last completed** (this session):
  - **`WIZ-045`** ✅ FIXED (master 2.11.30, `1705628d`) — ROM `do_goto`
    (`src/act_wiz.c:969-994`) sends the bamfout/bamfin (or default swirling-mist)
    line via `act(..., rch, TO_VICT)` **only** to room occupants where
    `get_trust(rch) >= ch->invis_level`, so a wiz-invis immortal's
    departure/arrival is **suppressed entirely** for sub-trust witnesses (gated on
    `invis_level` only, not full `can_see`). Python's `do_goto` routed both bamf
    broadcasts through `_act_room`, which `$n`→`char.name`-substitutes once and
    sends to every occupant — no gate, leaking the immortal's identity. New
    `_act_room_invis_gated` helper applies the per-recipient gate; `do_goto`'s four
    bamf calls use it. Shared `_act_room` left untouched (used by `do_transfer`,
    whose ROM path is a plain `act(TO_ROOM)` + PERS, no `invis_level` gate). Tests:
    `tests/integration/test_act_wiz_command_parity.py::test_goto_suppresses_bamf_for_subtrust_witnesses_when_wizinvis`
    + `::test_goto_bamf_visible_to_all_when_not_wizinvis`.
  - **`INV-027` candidate** corrected (master `077aae18`) — the watch-list entry
    claimed ROM `act()` suppresses the whole line for sub-trust witnesses; that is
    **wrong** (`act_new` `src/comm.c:2230-2244` delivers to all; visibility is
    `$n`→`PERS`/`can_see` name-masking to "someone", not line-suppression).
    Re-scoped as **ACT-PERS-NAME-MASKING** (concrete violation:
    `mud/utils/act.py:act_format._pers` lacks `can_see`); the genuine
    line-suppression is per-command in `do_goto`/`do_violate` → tracked as
    WIZ-045/WIZ-046. Left an open watch-list candidate.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_WIZ_045_DO_GOTO_WIZINVIS_GATE.md](SESSION_SUMMARY_2026-05-29_WIZ_045_DO_GOTO_WIZINVIS_GATE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.30 |
| Tests | 4982 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | Cross-file invariants (INV-027 candidate corrected/re-scoped; WIZ-046 open follow-up) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **`WIZ-046`** — close `do_violate`'s wizinvis bamf-announce gate (same
   `_act_room` root cause as WIZ-045, ROM `src/act_wiz.c:1026-1057`). The
   `_act_room_invis_gated` helper from this session is ready to reuse; smallest
   and most well-defined. One test, one commit.
2. **INV-027 (ACT-PERS-NAME-MASKING) probe** — verify which `act_format` callers
   are per-recipient (masking applies) vs `recipient=None` broadcast-once (fed to
   `broadcast_room` — the MESSAGE_DELIVERY.md divergence, can't reproduce ROM's
   per-recipient PERS), then route `act_format._pers` through `vision.pers()` and
   reconcile the two `_act_room` helpers. Promote to INV-027 ENFORCED if tractable.
3. Fresh cross-file probe in an area not yet covered by an INV row (affect ticks,
   position transitions, mob script triggers, group/follower chain) — probe-
   then-scope per AGENTS.md "Cross-File Invariants".

Carried-open items (see the summary's Outstanding): pet-shop haggle/"now follows
you" wrong-channel (INV-001 family, mailbox-only); `Character.pet` stale type
annotation; `do_cast` object-targeting legs; converter hardening; the
`test_backstab_uses_position_and_weapon` / `test_combat_death.py` xdist flakes.
