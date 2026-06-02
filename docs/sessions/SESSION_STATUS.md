# Session Status — 2026-06-02 — INV-025 object/equipment/give PERS sweep COMPLETE (2.12.54)

## Current State

- **Active mode**: cross-file invariants. The **INV-025 baked-name PERS
  re-probe is now EXHAUSTED** across `mud/commands/`, `mud/combat/`,
  `mud/skills/`, `mud/world/` — every confirmed `act_format(recipient=None)` /
  baked-`room.broadcast` / baked-f-string `act(TO_ROOM)` site renders through the
  shared `act_to_room` helper (per-recipient PERS masking + per-NPC TRIG_ACT).
- **This session — three batches (all committed locally, NOT pushed):**
  - **2.12.52** (`733a741d`) — object commands: `obj_manipulation.py` (put×4,
    remove, sacrifice×2, quaff), `inventory.py` (get×2, drop×3, smoke), 
    `consumption.py` (eat/drink/choke×2), `liquids.py` (fill/pour/pour-out),
    `magic_items.py` (`_broadcast` helper → `act_to_room`: recite/brandish/zap).
    `act_format(recipient=None)+broadcast_room` baked the actor name → collapsed
    each `broadcast_room`+`mp_act_trigger_room` pair into one `act_to_room`.
    Reconciled RECITE-002/BRANDISH-004/ZAP-004. Test
    `test_inv025_obj_command_pers_sweep.py` (7).
  - **2.12.53** (`379baa0b`) — `equipment.py` baked `f"{ch.name} …"` f-strings
    (wear/wield/hold/light/remove/level-fail) → `act_to_room`; **hold line gained
    ROM's `$s` gendered possessive** (was literal "their hand"). Reconciled
    WEAR-004. Test `test_inv025_equipment_pers_sweep.py` (5).
  - **2.12.54** (`4b6a012e`) — `give.py`: object branch → `disable_mobtrigger()`-
    wrapped `act_to_room` (TRIG_ACT stays suppressed per ROM `act_obj.c:832`;
    `mp_give_trigger` unchanged); **coins branch gained the missing TRIG_ACT**
    (ROM `:726` is unsuppressed). Removed the now-unused
    `_broadcast_to_room_observers`. Reconciled the `do_give` row + the obsolete
    `test_inv025_do_give_act_trigger_suppression.py`. Test
    `test_inv025_give_pers_sweep.py` (4).
- Discovery vs the literal prior task: `mud/combat/`, `mud/world/`, and
  `communication.py` (`do_say`/`do_tell`/`do_shout`) were **already swept**; the
  real remaining divergence was the object-command `act_format(recipient=None)`
  class. Advisor-reviewed scope; `give` split out for its inverse TRIG_ACT contract.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INV025_OBJ_EQUIP_GIVE_PERS.md](SESSION_SUMMARY_2026-06-02_INV025_OBJ_EQUIP_GIVE_PERS.md)
  (prior: [INV025_COMBAT_DEATH_PERS_TRIGACT](SESSION_SUMMARY_2026-06-01_INV025_COMBAT_DEATH_PERS_TRIGACT.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.54 |
| Tests | **full suite green: 5281 passed, 4 skipped** (run `pytest -p no:xdist -o addopts="" -q`; under high load `-n auto` hangs at worker fork and `-n0` can hit a broken xdist `sessionfinish` teardown) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | **None in the INV-025 PERS class** — the baked-name re-probe is exhausted across `mud/commands/`, `mud/combat/`, `mud/skills/`, `mud/world/`. |

## Next Intended Task

The INV-025 baked-name PERS re-probe is complete. Move to the next cross-file
invariants candidate (per AGENTS.md probe-then-scope method):

1. **Mob script trigger ordering** — TRIG_ENTRY/GREET/GIVE/BRIBE dispatch order vs
   ROM (e.g. portal/move ENTRY-vs-GREET, give MOBtrigger interactions). Read the
   ROM trigger site → Python equivalent → one failing contract test.
2. **Position transitions** — `update_pos`/`apply_position_change` edges (the
   INV-016 family) for any unguarded path.
3. **Group/follower chains** — leader-death/extract cascade, charm-break ordering.

Run a 5-minute probe; close as a single gap-closer commit or file the next free
INV-NNN in `CROSS_FILE_INVARIANTS_TRACKER.md`.

> **Push note:** everything through 2.12.48 is on `master`; **2.12.49–51**
> (FIGHT-041/042 + NUKEPET-001) and **2.12.52–54** (this session) are committed
> locally but **NOT yet pushed**. README/CHANGELOG/version all reflect 2.12.54.
> **Index:** GitNexus reindexed clean after the give commit; re-run after the
> docs/handoff commit.
