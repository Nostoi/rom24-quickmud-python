# Session Status — 2026-06-08 — INV-025 TRIG_ACT broadcast gaps (2.13.35)

## Current State

- **Active mode**: cross-file invariants / INV-025 ad-hoc follow-up sweep
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **5 missing TRIG_ACT dispatch sites fixed (INV-025 ad-hoc follow-ups).**
    Scavenger pickup `"$n gets $p."` (`mud/ai/__init__.py` — was baked f-string,
    now `act_to_room`). Four `char_update`/`_decay_worn_light` callsites in
    `mud/game_loop.py`: `"$n wanders on home."`, `"$n shivers and suffers."`,
    `"$n disappears into the void."`, `"$p goes out."` — all converted from
    `_message_room` to `_act_to_room`. 3 new enforcement tests added.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_INV025_TRIG_ACT_BROADCAST_GAPS.md](SESSION_SUMMARY_2026-06-08_INV025_TRIG_ACT_BROADCAST_GAPS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.35 |
| Tests | 5451 passing, 5 skipped (5456 collected) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 17 generated-oracle tests |
| INV-025 follow-up sites fixed | 5 (this session) |

## Next Intended Task

**Remaining INV-025 follow-up candidates:**

1. **Object decay / object affect wear-off TRIG_ACT** (`mud/game_loop.py:1214,
   1228, 1295, 1299`): `_broadcast_object_wear_off` and `_tick_obj_affects_in_room`
   use `_message_room` with pre-baked/rendered strings; ROM `src/update.c:1017-1022`
   calls `act(message, rch, obj, NULL, TO_ROOM)` (no `MOBtrigger = FALSE`). Fix
   requires either routing through `act_to_room` with `rch` as the actor, or adding
   a `mp_act_trigger_room` post-dispatch alongside the existing `_message_room`.

**Other cross-file invariant candidates:**

2. **Hypothesis state machine widening** (Class 11 Phase C, ongoing): add
   `give`/`lock`/`unlock`/`pick` command rules to `DeterministicNoRngDiffMachine`
   in `tools/diff_harness/generated.py`.
3. **`nuke_pets` lifecycle**: probe whether Python correctly extracts charmed
   followers on their master's death/extract (`src/handler.c:nuke_pets`).
4. **`TRIG_ENTRY` call-site coverage**: verify `mp_greet_trigger` fires when a
   mob enters a room — currently wired in `mud/world/movement.py` but not
   confirmed against all entry paths.
