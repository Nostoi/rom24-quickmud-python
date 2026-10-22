# Session Summary — 2026-07-16 — FIGHT-094 closed (check_killer inside damage())

## Scope

Autonomous loop iteration 8/10. Closed the long-standing carry-over
**FIGHT-094** — ROM `damage()` calls `check_killer` at `src/fight.c:733`;
Python only called it from the command layer.

## Outcomes

### `FIGHT-094` — ✅ FIXED

- **Python**: `mud/combat/engine.py:apply_damage` — `check_killer(attacker,
  victim)` inserted at ROM's exact position: after the is_safe re-check,
  BEFORE `set_fighting`.
- **ROM C**: `src/fight.c:733`; gates at `:1226-1285` (charm-thread follow,
  NPC/killer/thief victim early-outs, charm branch → `stop_follower`, and
  crucially the `ch->fighting == victim` early-out at `:1278`).
- **Assessment resolved the filed double-flagging concern**: ROM itself
  calls check_killer BOTH at the command layer AND inside damage() — the
  guards make repeat calls no-ops, and the damage()-layer call is the one
  that actually flags on the FIRST hit of a PvP engagement (fighting still
  NULL at that point).
- **Mirrored ROM consequence**: a CHARMED clan-PC who `kill`s a PC gets
  detached by the command-layer charm branch (`stop_follower` strips
  AFF_CHARM, `src/act_comm.c:1620-1624`) and is then FLAGGED by the first
  hit's damage()-layer call. The old
  `test_kill_with_charmed_attacker_stops_following_without_killer_flag`
  asserted "no flag" — it encoded the gap; rewritten to the ROM trace.
- **Tests**: `tests/integration/test_fight094_damage_check_killer.py` (3,
  failing-first: first-hit flags; established fight doesn't re-flag; NPC
  victim never flags).
- **Commit**: `0fe87f8f` (v2.14.330).

## Files Modified

- `mud/combat/engine.py` — check_killer in the damage() pre-application block
- `tests/integration/test_fight094_damage_check_killer.py` — new (3)
- `tests/test_combat.py` — stale charm/killer assertion rewritten
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-094 ✅ (inside the FIGHT-093 entry)
- `CHANGELOG.md`, `pyproject.toml` — 2.14.329 → 2.14.330

## Test Status

- Unit **2801 passed, 1 skipped**; integration **3441 passed, 3 skipped**.
- Differential harness: 102/102 across 69 scenarios.

## Next Steps

Remaining backlog: HANDLER-009 (test-only `MobInstance.move_to_room`
tail-append), DESC-001, OLC spell-name lookup, IS_BUILDER, stray db-file
cleanup. HANDLER-009 is the best-scoped next item.
