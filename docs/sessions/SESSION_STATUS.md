# Session Status — 2026-05-30 — WIZ-049 FIXED (INV-027 PERS contract fully enforced)

## Current State

- **Active mode**: cross-file invariants (the per-file audit tracker is
  exhausted — no ⚠️ Partial / ❌ Not Audited rows). This session closed
  **WIZ-049** (the `do_force` TO_VICT half of INV-027), completing the
  INV-027 (ACT-PERS-NAME-MASKING) contract — **no known `$n`/`$N` PERS-leak
  sites remain**.
- **Last completed** (this session):
  - **`WIZ-049`** ✅ FIXED (master 2.11.37, `a667507a`) — `do_force`'s four
    TO_VICT `"$n forces you to '<cmd>'."` lines (ROM `src/act_wiz.c:4205` + delivery
    at `:4228/4251/4274/4316`, `$n`=the forcer) now render via
    `mud/world/vision.py:pers(char, vch)` (single-target: `pers(char, victim)`) at
    all four sites (`imm_commands.py:339,354,369,399`), masking to `"someone forces
    you to '<cmd>'."` for a victim who cannot see the wiz-invis/invisible forcer.
    `gitnexus_impact` = LOW. Tests:
    `tests/integration/test_act_wiz_command_parity.py::test_force_masks_invisible_immortal_name_for_nonseeing_victim`
    + `::test_force_shows_immortal_name_to_seeing_victim`. Third and final PERS-leak
    sibling after WIZ-047 (TO_ROOM, 2.11.35) and WIZ-048 (`do_transfer` TO_VICT, 2.11.36).
  - **INV-027 milestone**: PERS masking now enforced across `act_format` (2.11.34),
    `_act_room`/TO_ROOM (WIZ-047), `do_transfer`/TO_VICT (WIZ-048), `do_force`/TO_VICT
    (WIZ-049). The only INV-027-adjacent item left open is the cross-cutting
    **ACT-FIRST-LETTER-CAP** capitalization divergence (→ INV-029; ⚠️ NOT
    INV-028 — that ID is already LIGHT-SLOT-KEY-COHERENCE).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-30_WIZ-049_FIXED.md](SESSION_SUMMARY_2026-05-30_WIZ-049_FIXED.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.37 |
| Tests | 4995 passed, 4 skipped, 0 failed (full parallel suite); includes the 2 new WIZ-049 tests |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | Cross-file invariants (INV-027 PERS fully enforced; ACT-FIRST-LETTER-CAP/INV-029 + VISION-002 OPEN) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **`ACT-FIRST-LETTER-CAP` → INV-029** (⚠️ NOT INV-028 — that ID is already
   LIGHT-SLOT-KEY-COHERENCE; next free is 029) — ROM `act_new` upper-cases the
   first letter of every rendered line (`src/comm.c:2376-2379`), with the `{`
   colour-code kludge (`buf[0]=='{'` → cap `buf[2]`, else `buf[0]`); the Python
   act-family does not. **Blast radius re-probed 2026-05-30 — wider than the
   earlier "single-point / masked-names-only" framing:** the faithful chokepoint
   `mud/utils/act.py:act_format` has **~80 call sites**, so capping its return
   flips the first letter of *every* act line — mostly no-ops (name-`$n` / "You"
   openers) but `$p` object-led lines (e.g. "a sword dissolves") legitimately
   become uppercase per ROM and break any test asserting the lowercase form.
   A **second render path** must also be covered: the `imm_commands` `pers()`-built
   f-strings (`do_force` ×4 `:339,354,369,399`, `do_transfer` `:282-290`,
   `_act_room`, bamf) do NOT route through `act_format`. Faithful close = a shared
   `capitalize_act_line` helper applied at both boundaries + a **full-suite
   assertion sweep** (incl. flipping the WIZ-047/048/049 `"someone"` → `"Someone"`
   cases in lockstep). **Do NOT land blind — needs a reliable channel to run the
   full suite.** Expanded scope: `CROSS_FILE_INVARIANTS_TRACKER.md` (INV-027
   watch-list) + `ACT_WIZ_C_AUDIT.md`.
2. **`VISION-002`** — the dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`: ROM masks on `room_is_dark(ch->in_room)` with no
   same-room guard). Larger scope (could shift cross-room/scan visibility); write
   a failing test first. Filed in `HANDLER_C_AUDIT.md`.
3. Fresh cross-file probe (affect ticks, position transitions, mob script
   triggers, group/follower chain).

Carried-open items: known **xdist flakes** (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon` — pass in isolation, can flake under some
parallel worker groupings); pet-shop haggle/"now follows you" wrong-channel
(INV-001 family, mailbox-only); `Character.pet` stale type annotation; `do_cast`
object-targeting legs; converter hardening. Non-blocking (ROM-faithful, not a
gap): `pers`/`_act_room` → `can_see_character` consumes an RNG draw on the sneak
branch — findability note only.

## Commit / push state

- **Pushed to `origin/master`**: WIZ-047 (`d7f88228` + doc-correction `40a5e289`)
  — the user said "push" for that batch.
- **Local-only, NOT pushed** (await the user's say-so): WIZ-048 (`66758fd1` +
  docs `f84a1c47`), WIZ-049 (`a667507a` + the session-docs commit).

> Tooling note: the Bash/Read/MCP output channels buffered heavily this session.
> Worked around via temp-file routing + `python3` prints + execute-ready handoff
> docs at each risk point. All "passing"/"FIXED" claims here were read from
> rendered output, not assumed. **Process rule reinforced**: `git show --name-only
> HEAD` after every commit (the WIZ-047 commit once silently dropped a staged file).
