# Session Status — 2026-05-30 — ACT-CAP-001 broadcast_room (INV-029 room-broadcast cousin CLOSED)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows). Today closed two INV-029 (ACT-FIRST-LETTER-CAP)
  cousins: **FIGHT-031** (combat broadcasts) then **ACT-CAP-001** (`broadcast_room`).
- **Last completed** (this leg):
  - **`ACT-CAP-001` (broadcast_room half)** ✅ FIXED (master 2.11.40, `4bc1acf4`)
    — `mud/net/protocol.py:broadcast_room` is the Python `act(TO_ROOM)` delivery
    boundary for ~64 command/skill/movement callers but delivered the baked
    string verbatim (uncapped). ROM `act_new` (`src/comm.c:2376-2379`) caps the
    first visible char. Fixed by capping the message **once at function entry**
    via `capitalize_act_line` (terminal primitive — one baked string for all
    recipients). `broadcast_global` deliberately NOT capped (mixed: channels are
    `act()`, weather is `send_to_char`). `gitnexus_impact` = CRITICAL (64 callers,
    0 processes — expected render change); `detect_changes` = low. Re-baselined
    **9** stale lowercase room-leg asserts. Test:
    `tests/integration/test_act_cap_001_broadcast_room.py` (3). Full suite 5010
    passed / 0 failed.
  - Surfaced + filed **`ACT-CAP-002`** (parallel uncapped primitives
    `Room.broadcast` + `_message_room`, and the TO_ALL caster legs in
    object-spell handlers — the `_send_to_char(caster, message)` leg ROM's
    `act(TO_ALL)` caps but Python does not).
- **Earlier today**: **FIGHT-031** ✅ FIXED (2.11.39, `1b69e449`) — combat
  `_broadcast_pos_change` + defense/flaming sites. See its summary.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-30_ACT-CAP-001_BROADCAST_ROOM.md](SESSION_SUMMARY_2026-05-30_ACT-CAP-001_BROADCAST_ROOM.md)
  (FIGHT-031 leg: [SESSION_SUMMARY_2026-05-30_FIGHT-031_COMBAT_ACT_CAP.md](SESSION_SUMMARY_2026-05-30_FIGHT-031_COMBAT_ACT_CAP.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.40 |
| Tests | 5010 passed, 4 skipped, 0 failed (full parallel suite; +3 ACT-CAP-001 tests) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants (INV-029 enforced at act_format + imm_commands + combat + broadcast_room; ⚠️ ACT-CAP-002 / do_say-do_tell / broadcast_global OPEN) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **`ACT-CAP-002`** (`docs/parity/FIGHT_C_AUDIT.md`) — the parallel room-broadcast
   primitives + TO_ALL caster legs left uncapped by ACT-CAP-001:
   - **`mud/models/room.py:Room.broadcast`** (~20 callers — death lines, "$n is
     zapped", mob actions, practice/level, reconnect/link-lost) — highest value;
     cap at its entry like `broadcast_room`. Expect a re-baseline surface.
   - The **TO_ALL caster legs** in the object-spell handlers (invis/poison/
     remove_curse/portal/nexus) — cap the shared `message` at each build site so
     the caster `_send_to_char` leg matches ROM `act(TO_ALL)`; re-baseline the
     caster-side asserts the ACT-CAP-001 sweep left lowercase (with comments).
   - `mud/game_loop.py:_message_room` (object wear-off).
2. **`do_say` / `do_tell`** (`mud/commands/communication.py`) — INV-029 cousin
   (`test_tell_parity.py:19` notes the cap as a known deferral).
3. **`broadcast_global`** — per-channel cap, NOT a blanket chokepoint (weather is
   `send_to_char`).
4. **`FIGHT-032`/`033`/`034`** — combat PERS / FROST-SHOCKING `$p` / auto-split
   (filed in the FIGHT-031 session).
5. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`). Larger scope; failing test first.

Carried-open: known **xdist flakes** (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); pet-shop haggle / "now follows you"
wrong-channel (INV-001 family); `Character.pet` stale type annotation; `do_cast`
object-targeting legs.

## Commit / push state

- Today: `1b69e449` (FIGHT-031 code) + `7151e2fd` (FIGHT-031 handoff) +
  `4bc1acf4` (ACT-CAP-001 code) + the upcoming ACT-CAP-001 handoff-docs commit.
- **Local-only, NOT pushed** — await the user's say-so before pushing to
  `origin/master`. (`master` was in sync with `origin/master` at session start.)
- One unrelated pre-existing working-tree change left unstaged:
  `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (present at session start).

> Process notes (carried): `git show --name-only HEAD` after every commit
> (verified all 11 landed for `4bc1acf4`). Re-baseline discipline: judge each
> failure individually — the invis wear-off "fades into view" line looked like a
> re-baseline but is delivered via `_message_room` (not broadcast_room), so it
> stayed lowercase. No bulk-sed.
