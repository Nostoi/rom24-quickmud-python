# Session Status — 2026-05-25 — INV-015 affect-tick lifecycle (2.9.7)

## Current State

- **Active pass**: cross-file invariants — INV-015 AFFECT-TICK-LIFECYCLE
  closed. Probe-then-scope worked end-to-end again: 5-minute read of
  `src/update.c:affect_update` + `src/handler.c:affect_remove` plus
  the Python equivalents surfaced a real stat-leak + phantom-bit
  divergence in `mud/affects/engine.py:tick_spell_effects`. Filed as
  INV-015, closed in one commit with two enforcement tests.
- **Last completed**: `v2.9.7` (commit `266056c`) — `affect_remove`
  added at module level in `mud/handler.py`; `tick_spell_effects`
  expiry branch split between ROM-canonical entries (route through
  `affect_remove`) and spell-effects-managed shadow mirrors (bare
  list removal, `remove_spell_effect` handles their stat unwind).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-25_INV015_AFFECT_TICK_LIFECYCLE.md](SESSION_SUMMARY_2026-05-25_INV015_AFFECT_TICK_LIFECYCLE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.7 |
| Tests | 4714 passed, 4 skipped, 0 failed |
| Cross-file invariants | 15 of ~20 budget; INV-001 … INV-015 all ✅ ENFORCED |
| Branch | `master` (commit `266056c` ready for `v2.9.7` tag + push) |
| Watch list | Empty. |

## Next Intended Task

The default per-file audit path remains exhausted; the cross-file
invariants pass is the active mode. INV-015 closed cleanly without
spilling sibling gaps into the same commit. Two candidates for the
next probe (ordered):

1. **Sibling affect-removal sweep** (option #2 from the 2.9.7 menu):
   `Character.affect_remove` (`mud/models/character.py:862`) and
   `Character.remove_spell_effect` both touch the affect list
   without going through the new module-level `affect_remove`. The
   former has zero callers today; the latter is integrated into the
   tick-path split, so the path is correct but the helper itself
   isn't a single canonical removal point. One targeted gap-closer
   each — belt-and-suspenders before the helper gets new callers.
2. **Position transitions** (option #3): POS_DEAD ↔ POS_INCAP ↔
   POS_STUNNED ↔ POS_SLEEPING ↔ POS_STANDING. Partial coverage via
   INV-002 (death/prompt) and INV-004 (PC death/connection); the
   full transition table per `src/fight.c:update_pos`,
   `src/act_info.c:do_wake/do_sleep`, `src/handler.c:position_lookup`
   isn't pinned.
3. **Mob script triggers** (option #4 from the cluster-end menu):
   ENTRY / GIVE / KILL / RANDOM / HPCNT firing across `mob_cmds`,
   `game_loop`, `handler`, command dispatcher — not yet probed.
