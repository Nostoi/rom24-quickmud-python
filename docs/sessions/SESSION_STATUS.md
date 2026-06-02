# Session Status — 2026-06-02 — INV-025 `act_format`/broadcast command group CLOSED (socials class still open) + doors rework + `_pers` fidelity (2.12.55)

## Current State

- **Active mode**: cross-file invariants. The **INV-025 `act_format` /
  inline-f-string / `.format`-baked `broadcast_room` command group is now
  CLOSED** across `mud/commands/` (verified by an ALL-broadcast residual sweep —
  `broadcast_room|\.broadcast(` + `for … in ….people`, every call eyeballed).
  This 4th batch closed the group the prior three (object / equipment / give)
  walked past, fixed two latent `act_format._pers` divergences from ROM `PERS`,
  and — after an advisor catch that the inline-`f"` grep alone was insufficient —
  swept two more stragglers (`do_pose`, `do_incognito`). **One distinct
  `$n`-baking class remains in `mud/commands/`: the socials `expand_placeholders`
  group** (see Next Intended Task) — it is a separate mechanism and is NOT
  claimed closed.
- **This session — two commits (local, NOT pushed):**
  - **2.12.55 / `e020127d`** — command-layer broadcast PERS sweep: `position.py`
    (rest/sit/sleep/stand), `session.py` (quit), `inspection.py` (scan/peer `$T`),
    `healer.py` (utter `$T`), `imm_load.py` (mload `$N`/oload `$p`/purge room/`$N`
    TO_NOTVICT — dropped `_notvict_broadcast`), `imm_search.py` (clone `$p`/`$N`),
    `shop.py` (buy-pet `$N`/buy-item `$p[N]`/sell `$p` — **adds the missing
    TRIG_ACT**, masking unreachable via keeper-can-see gate). **`do_restore`
    TO_VICT** → `act_format(recipient=victim)` (self-restore keeps the name).
    Also swept `communication.py:do_pose` (`act_comm.c:1425`) and
    `admin_commands.py:_broadcast_incog_message` (`act_wiz.c:4389/4395/4412`) —
    advisor-surfaced stragglers in the same class (dropped orphaned
    `_resolve_display_name`/`_possessive_pronoun`). **`act_format._pers`** aligned
    with `vision.pers`: NPC→short_descr (was `name`), removed the non-ROM `"You"`
    self-case. Tests: `test_inv025_command_broadcast_pers_sweep.py` (incl.
    pose/incog) + shop buy TRIG_ACT.
  - **2.12.55 / `5299c664`** — `doors.py:_broadcast_act_to_room` reworked from a
    pre-baked `f"{actor_name} …"` string to a ROM `act()` format string +
    `act_to_room`; all 15 open/close/lock/unlock/pick callers converted
    (`$p`/`$d`). Test `test_inv025_door_commands_pers_sweep.py` (7). Carries the
    version bump + CHANGELOG/README/tracker doc updates.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INV025_COMMAND_BROADCAST_DOORS_PERS.md](SESSION_SUMMARY_2026-06-02_INV025_COMMAND_BROADCAST_DOORS_PERS.md)
  (prior: [INV025_OBJ_EQUIP_GIVE_PERS](SESSION_SUMMARY_2026-06-02_INV025_OBJ_EQUIP_GIVE_PERS.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.55 |
| Tests | **full suite green: 5306 passed, 4 skipped** (`pytest -p no:xdist -o addopts="" -q`, ~9.5m) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | **INV-025 socials `expand_placeholders` `$n` class still OPEN** (see Next Intended Task). The `act_format`/inline-f-string/`.format`-baked `broadcast_room` command group is closed. |

## Next Intended Task

**First: close the INV-025 socials `$n` PERS class** — the last `$n`-baking
room-broadcast in `mud/commands/`. `mud/commands/socials.py` renders
`social.others_found`/`others_auto`/`others_no_arg` via
`mud/models/social.py:expand_placeholders`, which replaces `$n`→`actor.name`
with **no `can_see` masking and no per-recipient PERS**, then `room.broadcast`s
the one baked string (also **no TRIG_ACT**). ROM uses `act(social.others_*, ch,
victim, TO_ROOM/TO_NOTVICT)` per recipient (`src/act_comm.c:do_social` / `interp.c`
social dispatch). This is a distinct mechanism (not `act_format`) over ~244
socials with victim TO_NOTVICT handling — scope it as its own batch (probe →
failing masking test → convert `socials.py` to `act_to_room`, likely
generalizing `expand_placeholders` or routing through `act_format`). The
`do_say`/`do_tell`/`do_shout` per-recipient `pers()` loops are already correct.

**Then** the remaining cross-file-invariants candidates (probe-then-scope):

1. **Mob script trigger ordering** — TRIG_ENTRY / TRIG_GREET / TRIG_GIVE /
   TRIG_BRIBE fire-order vs ROM (`src/mob_prog.c`, `mob_cmds.c`).
2. **Position transitions** — sleeping/resting/sitting/standing/fighting edges.
3. **Group / follower chains** — `add_follower`/`die_follower`/`stop_follower`.

> **Push note:** everything through 2.12.48 is on `master`; **2.12.49–55** are
> committed locally but **NOT yet pushed**. README/CHANGELOG/version all reflect
> 2.12.55. Reindex GitNexus after the docs/handoff commit.
