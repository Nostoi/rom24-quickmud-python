# Session Status — 2026-05-30 — FIGHT-031 Combat act() Capitalization (INV-029 combat cousin CLOSED)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows). This session closed the **combat** cousin of
  **INV-029** (ACT-FIRST-LETTER-CAP) as **FIGHT-031**.
- **Last completed** (this session):
  - **`FIGHT-031`** ✅ FIXED (master 2.11.39, `1b69e449`) — ROM `act_new`
    (`src/comm.c:2376-2379`) caps the first visible char of every `act()` line.
    Capped the two combat render boundaries that bypassed `render_for` (FIGHT-025
    had already capped the `dam_message` chokepoint): **(a)** `_broadcast_pos_change`
    (the per-listener PERS render for the position-change room broadcasts
    mortal/incap/stunned/DEAD + all 5 weapon-special room broadcasts), capping
    each line + the `canonical` fed to `mp_act_trigger_room`; **(b)** the
    direct-f-string defense TO_CHAR lines (parry/dodge/shield-block) + the flaming
    victim line, via `capitalize_act_line`. The POISON victim line
    (`src/fight.c:612` `send_to_char`, NOT `act()`) is correctly left uncapped —
    each site verified `act()` vs `send_to_char` against `src/fight.c:595-682`.
    `gitnexus_impact(_broadcast_pos_change)` = CRITICAL (27 impacted, 0 processes,
    expected render-behaviour change); `detect_changes` = low. Full-suite sweep
    flipped **3** stale lowercase asserts (flaming `"test weapon"`→`"Test weapon"`
    ×2; FIGHT-007 `"someone is DEAD!!"`→`"Someone is DEAD!!"` — INV-027 mask +
    INV-029 cap composing). Test:
    `tests/integration/test_fight_031_combat_act_capitalization.py` (5).
  - **Handoff reconciliation**: the prior status named "the goblin misses you"
    (the `dam_message` miss line) as the top uncapped combat path — but FIGHT-025
    had already capped that. FIGHT-031 closed the *real* remaining combat act()
    sites; the combat damage path is now fully CLOSED.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-30_FIGHT-031_COMBAT_ACT_CAP.md](SESSION_SUMMARY_2026-05-30_FIGHT-031_COMBAT_ACT_CAP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.39 |
| Tests | 5007 passed, 4 skipped, 0 failed (full parallel suite; includes 5 new FIGHT-031 tests) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants (INV-029 combat chokepoints ENFORCED; ⚠️ `broadcast_room`/`do_say`/`do_tell` cousins OPEN) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **Close the remaining INV-029 / ACT-CAP-001 cousins** (each its own
   failing-first test + commit — these direct-f-string `act()` sites still
   bypass capping, so a reader must NOT assume act-capitalization is fully
   locked):
   - **`broadcast_room`/`broadcast_global`** (`mud/net/protocol.py`) — the
     remaining non-combat act()-broadcast chokepoint named by **ACT-CAP-001**.
     Cap at the render boundary; expect a **wide** re-baseline surface (many
     tests assert lowercase room/broadcast strings). Do this one first.
   - **`do_say` / `do_tell`** (`mud/commands/communication.py` build
     `"{6$n says…"` / `"{k$n tells you…"`; `test_tell_parity.py:19` notes the cap
     as a known deferral).
   - Lesser: the wiznet `WIZ_PREFIX` `"{Z--> "` path (prefix-on case only,
     unexercised).
2. **`FIGHT-032` / `FIGHT-033` / `FIGHT-034`** — combat cousins filed this
   session (`docs/parity/FIGHT_C_AUDIT.md` Follow-ups): defense lines bypass
   PERS (INV-027 family); FROST/SHOCKING victim lines drop `$p`; auto-split line
   uncapped + bypasses PERS. Each its own commit.
3. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`; `HANDLER_C_AUDIT.md`). Larger scope; failing test first.
   Do NOT fold into the same session as the cousins.
4. Fresh cross-file probe (affect ticks, position transitions, mob script
   triggers, group/follower chain).

Carried-open: known **xdist flakes** (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon` — pass in isolation, can flake under
some parallel worker groupings; this session's full run had 0 failures);
pet-shop haggle / "now follows you" wrong-channel (INV-001 family, mailbox-only);
`Character.pet` stale type annotation; `do_cast` object-targeting legs.

## Commit / push state

- This session: `1b69e449` (FIGHT-031 code, 8 files) + the handoff-docs commit
  (this status + summary + `README.md` badge/metric refresh to 2.11.39 / 5007).
- **Local-only, NOT pushed** — await the user's say-so before pushing to
  `origin/master`. (`master` was in sync with `origin/master` at session start.)
- One unrelated pre-existing working-tree change left unstaged:
  `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (present at session start).

> Process notes (carried): `git show --name-only HEAD` after every commit (a WIZ-047
> commit once silently dropped a staged file — verified all 8 landed for `1b69e449`).
> The test/MCP channels were reliable this session.
