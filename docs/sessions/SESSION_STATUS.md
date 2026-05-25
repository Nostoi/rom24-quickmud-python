# Session Status — 2026-05-25 — INV-015 + INV-015 dead-code sweep + INV-016 filed (2.9.7 → 2.9.9)

## Current State

- **Active pass**: cross-file invariants. Three clusters across the
  2026-05-25 session — all the same probe-then-scope pattern.
  - **2.9.7** — INV-015 AFFECT-TICK-LIFECYCLE closed (✅ ENFORCED).
    `mud/handler.py:affect_remove` added; `tick_spell_effects`
    expiry branch split between ROM-canonical (route through
    `affect_remove`) and spell-effects-managed shadow mirrors
    (bare list removal — `remove_spell_effect` handles their stat
    unwind, double-routing would double-unwind). Two enforcement
    tests.
  - **2.9.8** — sibling sweep on the INV-015 surface. Deleted dead
    `Character.affect_remove` (zero callers, would have resurfaced
    the same stat-leak if anyone wired it in).
  - **2.9.9** — INV-016 BCAST-ON-POSITION-TRANSITION filed
    ❌ BROKEN with xfail(strict=True) documenting test. Damage
    spells in `mud/skills/handlers.py` bypass `apply_damage`, so
    spell-induced INCAP/MORTAL/DEAD transitions are silent to the
    room. Sibling of INV-001 but inverted (zero-delivery). ~18
    spell sites; closing is a separate cluster.
- **Last completed**: commit `4116962` on master.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-25_INV015_AFFECT_TICK_LIFECYCLE.md](SESSION_SUMMARY_2026-05-25_INV015_AFFECT_TICK_LIFECYCLE.md)
  (covers the 2.9.7 cluster; 2.9.8 + 2.9.9 are CHANGELOG-only).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.9 |
| Tests | 4714 passed, 1 xfailed (INV-016 documenting), 4 skipped, 0 failed |
| Cross-file invariants | 16 of ~20 budget; INV-001 … INV-015 ✅ ENFORCED; INV-016 ❌ BROKEN |
| Branch | `master` (tags `v2.9.7` pushed; `v2.9.8` + `v2.9.9` queued) |
| Watch list | INV-016 closure (~18 spell sites). |

## Next Intended Task

INV-016 closure is the queued cluster. Two design choices:

1. **Route every damage-spell handler in `mud/skills/handlers.py`
   through `mud/combat/engine.py:apply_damage`** — semantically
   correct (matches ROM's "all damage funnels through `damage()`"
   shape) but a wide refactor: ~18 spell sites change call
   structure, and `apply_damage` carries combat-specific side
   effects (autoflee triggers, fighting setup, kill XP) that need
   filtering for spell paths.
2. **Factor `_position_change_message` out of
   `mud/combat/engine.py:_apply_damage` and call it directly from
   each spell site after `update_pos`** — minimal blast radius.
   One helper invocation per spell, no behavioral change to
   `apply_damage`. Probably the right shape if `apply_damage`
   carries side effects we don't want firing on spell damage.

Recommend #2 — file as INV-016-CLOSE cluster, one commit per
spell site (or one commit batching by spell family — acid,
breath, harm, etc.) until the xfail flips to passing strict-fail.

Other candidates that remain unprobed:

- **Mob script triggers** (ENTRY / GIVE / KILL / RANDOM / HPCNT
  firing across mob_cmds, game_loop, handler, dispatcher) —
  candidate area #3 from the 2026-05-25 prompt.
- **Group / follower chain** — leader/master pointers, group XP
  split, follow propagation, disband-on-death — candidate area
  #4 from the 2026-05-25 prompt.
