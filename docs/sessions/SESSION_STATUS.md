# Session Status — 2026-05-30 — INV-029 ACT-FIRST-LETTER-CAP ENFORCED

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows). This session promoted **ACT-FIRST-LETTER-CAP**
  to a stable cross-file invariant (**INV-029**) and enforced it.
- **Last completed** (this session):
  - **`INV-029` (ACT-FIRST-LETTER-CAP)** ✅ ENFORCED (master 2.11.38, `7e9c488c`)
    — ROM `act_new` caps the first visible letter of every rendered `act()` line
    (`src/comm.c:2376-2379`, `{`-colour-code kludge → cap `buf[2]` else `buf[0]`,
    ASCII-only UPPER). Enforced via new shared helper
    `mud/utils/act.py:capitalize_act_line` applied at the two render boundaries:
    `act_format`'s return (~113 call sites) and the `imm_commands` `pers()`-built
    f-strings that bypass it (`do_force` ×4, `do_transfer`, `_act_room`,
    `_act_room_invis_gated`). `gitnexus_impact(act_format)` = CRITICAL (43 callers,
    expected — deliberate render-behaviour change); `detect_changes` = low, 0
    affected processes. Full-suite sweep flipped **15** now-stale lowercase
    assertions to their ROM-correct capitalized form (incl. the WIZ-047/048/049
    `"someone"` → `"Someone"` lockstep). Test:
    `tests/integration/test_inv029_act_first_letter_cap.py` (7).
  - **INV-027 ↔ INV-029 milestone**: with INV-029 enforced, the act-rendering
    parity for masked names is complete at the `act_format` + `imm_commands`
    chokepoints — masked `$n` now renders `"Someone …"` (capitalized) as ROM does.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-30_INV-029_ACT_FIRST_LETTER_CAP.md](SESSION_SUMMARY_2026-05-30_INV-029_ACT_FIRST_LETTER_CAP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.38 |
| Tests | 5002 passed, 4 skipped, 0 failed (full parallel suite; includes 7 new INV-029 tests) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants (INV-029 ENFORCED at chokepoints; ⚠️ direct-f-string cousins OPEN) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **Close the INV-029 cousins** (now concrete + scoped — these are direct
   f-string `act()` sites that bypass `act_format` and are still uncapped, so a
   reader must NOT assume act-capitalization is fully locked):
   - **High-frequency combat damage messages** (`mud/combat/messages.py` /
     `mud/combat/engine.py`) — e.g. `"the goblin misses you"` → ROM
     `"The goblin misses you"`. Highest-traffic uncapped act path; do this first.
   - **`do_say` / `do_tell`** (`mud/commands/communication.py` build
     `"{6$n says…"` / `"{k$n tells you…"` f-strings; `test_tell_parity.py:19`
     already notes the cap as a known deferral).
   - Lesser: wiznet `WIZ_PREFIX` `"{Z--> "` path (Python caps inner message vs
     ROM's `buf[2]`=`-` no-op; prefix-on case only, unexercised).
   - Close each via `capitalize_act_line` with its own failing-first test.
     See `CROSS_FILE_INVARIANTS_TRACKER.md` INV-029 status cell.
2. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`; `HANDLER_C_AUDIT.md`). Larger scope; failing test first.
   Do NOT fold into the same session as the cousins.
3. Fresh cross-file probe (affect ticks, position transitions, mob script triggers,
   group/follower chain).

Carried-open: known **xdist flakes** (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon` — pass in isolation, can flake under
some parallel worker groupings; this session's full run had 0 failures);
pet-shop haggle / "now follows you" wrong-channel (INV-001 family, mailbox-only);
`Character.pet` stale type annotation; `do_cast` object-targeting legs.

## Commit / push state

- This session: `7e9c488c` (INV-029 code, 14 files) + the handoff-docs commit
  (this status + summary + `CROSS_FILE_INVARIANTS_TRACKER.md` status-cell honesty
  fix + `README.md` badge/metric refresh to 2.11.38 / 5002).
- **Local-only, NOT pushed** — await the user's say-so before pushing to
  `origin/master`. (`master` was in sync with `origin/master` at session start.)

> Process notes (carried): `git show --name-only HEAD` after every commit (a WIZ-047
> commit once silently dropped a staged file — verified all 14 landed for `7e9c488c`).
> The test/MCP channels were reliable this session (the WIZ-049 buffering did not recur).
