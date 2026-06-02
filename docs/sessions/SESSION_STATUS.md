# Session Status — 2026-06-02 — INV-025 command-layer broadcast PERS sweep CLOSED + doors rework + `_pers` fidelity (2.12.55)

## Current State

- **Active mode**: cross-file invariants. The **INV-025 command-layer
  `broadcast_room` / `act_format(recipient=None)` PERS class is now EXHAUSTED**
  across `mud/commands/` — verified by a residual grep
  (`broadcast_room(.*f"` / `.broadcast(f"`) that returns only the no-`$n` door
  reverse line. This 4th batch closed the group the prior three (object /
  equipment / give) walked past, and surfaced + fixed two latent
  `act_format._pers` divergences from ROM `PERS`.
- **This session — two commits (local, NOT pushed):**
  - **2.12.55 / `e020127d`** — command-layer broadcast PERS sweep: `position.py`
    (rest/sit/sleep/stand), `session.py` (quit), `inspection.py` (scan/peer `$T`),
    `healer.py` (utter `$T`), `imm_load.py` (mload `$N`/oload `$p`/purge room/`$N`
    TO_NOTVICT — dropped `_notvict_broadcast`), `imm_search.py` (clone `$p`/`$N`),
    `shop.py` (buy-pet `$N`/buy-item `$p[N]`/sell `$p` — **adds the missing
    TRIG_ACT**, masking unreachable via keeper-can-see gate). **`do_restore`
    TO_VICT** → `act_format(recipient=victim)` (self-restore keeps the name).
    **`act_format._pers`** aligned with `vision.pers`: NPC→short_descr (was
    `name`), and removed the non-ROM `"You"` self-case. Tests:
    `test_inv025_command_broadcast_pers_sweep.py` (14) + shop buy TRIG_ACT.
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
| Tests | **full suite green: 5303 passed, 4 skipped** (`pytest -p no:xdist -o addopts="" -q`, ~10m) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | **none in the INV-025 command-layer PERS class** (exhausted this session). |

## Next Intended Task

The INV-025 PERS sweep is complete for `mud/commands/`. Move to the remaining
**cross-file invariants** candidates (per AGENTS.md probe-then-scope method):

1. **Mob script trigger ordering** — TRIG_ENTRY / TRIG_GREET / TRIG_GIVE /
   TRIG_BRIBE fire-order vs ROM (`src/mob_prog.c`, `mob_cmds.c`).
2. **Position transitions** — sleeping/resting/sitting/standing/fighting edges
   and the act() lines they emit (cross-check vs `act_move.c`).
3. **Group / follower chains** — `add_follower`/`die_follower`/`stop_follower`
   and charm/pet membership invariants.

Run a 5-minute probe (read ROM C contract → read Python equivalent → write one
failing test), then either close as a single gap-closer commit or file as the
next free INV-NNN.

> **Push note:** everything through 2.12.48 is on `master`; **2.12.49–55** are
> committed locally but **NOT yet pushed**. README/CHANGELOG/version all reflect
> 2.12.55. Reindex GitNexus after the docs/handoff commit.
