# Session Status — 2026-05-29 — WIZ-048 FIXED (INV-027 PERS contract — `do_transfer` TO_VICT half)

## Current State

- **Active mode**: cross-file invariants (the per-file audit tracker is
  exhausted — no ⚠️ Partial / ❌ Not Audited rows). This session closed
  **WIZ-048** (the `do_transfer` TO_VICT half of INV-027), pushed the prior
  session's WIZ-047 commits to `origin/master`, and filed two new durable items
  (**WIZ-049** OPEN, **ACT-FIRST-LETTER-CAP** OPEN).
- **Last completed** (this session):
  - **`WIZ-048`** ✅ FIXED (master 2.11.36, `5cb1c4f8`) — `do_transfer`'s victim
    notify `"$n has transferred you."` (ROM `src/act_wiz.c:874-875`, TO_VICT,
    `$n`=the immortal) now renders via `mud/world/vision.py:pers(char, victim)`
    (`imm_commands.py:282-290`), masking to `"someone has transferred you."` for a
    victim who cannot see the wiz-invis/invisible immortal. `gitnexus_impact` =
    LOW (`do_transfer` only reachable via `do_teleport`). Tests:
    `tests/integration/test_act_wiz_command_parity.py::test_transfer_masks_invisible_immortal_name_for_nonseeing_victim`
    + `::test_transfer_shows_immortal_name_to_seeing_victim`. The TO_VICT sibling
    of WIZ-047 (TO_ROOM, 2.11.35); together they close the `imm_commands.do_transfer`
    half of the INV-027 (ACT-PERS-NAME-MASKING) contract.
  - This commit also **repaired the INV-027 tracker prose lost from the WIZ-047
    commit** (`d7f88228` committed 5 files; that session's
    `CROSS_FILE_INVARIANTS_TRACKER.md` edit silently did not land). The tracker now
    records WIZ-047 + WIZ-048 FIXED and WIZ-049 OPEN.
  - **`WIZ-049`** ❌ FILED OPEN (master 2.11.36 doc, `5cb1c4f8`) — `do_force`'s
    four TO_VICT `"$n forces you to '<cmd>'."` lines (ROM `src/act_wiz.c:4205,4228,4251,4274,4316`,
    `$n`=the forcer) render the raw name (`imm_commands.py:327,342,357,387`),
    leaking a wiz-invis immortal's identity to forced victims. Same INV-027
    contract, different command. Filed in `ACT_WIZ_C_AUDIT.md` + cross-ref'd from INV-027.
  - **`ACT-FIRST-LETTER-CAP`** ❌ FILED OPEN (→ future INV-028) — ROM `act_new`
    upper-cases `buf[0]` of every rendered line (`src/comm.c:2376-2379`); the
    Python act-family does not. Only visible on the masked `"someone"` case (ROM:
    `"Someone …"`). Single-point fix at the act-render boundary. WIZ-047/048 tests
    assert lowercase deliberately, to move in lockstep when closed.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_WIZ-048_FIXED.md](SESSION_SUMMARY_2026-05-29_WIZ-048_FIXED.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.36 |
| Tests | 4993 passed, 4 skipped, 0 failed (full parallel suite); includes the 2 new WIZ-048 tests |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | Cross-file invariants (INV-027: WIZ-047 + WIZ-048 FIXED; WIZ-049 + ACT-FIRST-LETTER-CAP + VISION-002 OPEN) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **`WIZ-049`** — `do_force`'s four TO_VICT `"$n forces you to..."` leaks
   (`imm_commands.py:327,342,357,387`, ROM `src/act_wiz.c:4205+`). `rom-gap-closer`-able:
   failing per-recipient test (forced victim without detect-invis → "someone
   forces you to..."; with → name), then route all four sites through
   `mud/world/vision.py:pers(char, vch)`. One gap = one test = one commit. With
   WIZ-047 + WIZ-048 + WIZ-049 all closed, the INV-027 PERS contract is fully
   enforced across `act_format`, `_act_room` (TO_ROOM), `do_transfer` (TO_VICT),
   and `do_force` (TO_VICT).
2. **`ACT-FIRST-LETTER-CAP` → INV-028** — promote to a stable cross-file ID; add
   the single act-render-boundary capitalization step; flip the WIZ-047/048/049
   lowercase `"someone"` assertions to `"Someone"` in lockstep.
3. **`VISION-002`** — the dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`). Larger scope; write a failing test first. Filed in
   `HANDLER_C_AUDIT.md`.
4. Fresh cross-file probe (affect ticks, position transitions, mob script
   triggers, group/follower chain).

Carried-open items: known **xdist flakes** (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon` — pass in isolation, can flake under some
parallel worker groupings); pet-shop haggle/"now follows you" wrong-channel
(INV-001 family, mailbox-only); `Character.pet` stale type annotation; `do_cast`
object-targeting legs; converter hardening. Non-blocking (ROM-faithful, not a
gap): `pers`/`_act_room` → `can_see_character` consumes an RNG draw on the sneak
branch — findability note only.

> Tooling note: the Bash/Read/MCP output channels buffered intermittently this
> session (empty returns, then recovery). Worked around via temp-file routing +
> `python3` prints. All "passing"/"FIXED" claims here were read from rendered
> output, not assumed. **Process catch**: always `git show --name-only HEAD`
> after a commit — the WIZ-047 commit silently dropped a staged file.
