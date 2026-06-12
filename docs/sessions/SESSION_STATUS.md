# Session Status — 2026-06-11 — FIGHT-058 damage reduction bypass fixed

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-058 — moved `apply_damage_reduction` inside `apply_damage`
  so all callers (spells, skills, weapon procs, mob programs, tick effects) get
  drunk/sanctuary/protection reductions; removed pre-call from `one_hit` to prevent
  double-reduction on the melee path. Completes the ROM `damage()` pipeline (FIGHT-056/057/058).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-11_FIGHT058_DAMAGE_REDUCTION_BYPASS.md](SESSION_SUMMARY_2026-06-11_FIGHT058_DAMAGE_REDUCTION_BYPASS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.4 |
| Tests | 5607/5607 passing, 4 skipped (2026-06-11) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

**INV-044 cross-file probe** — three candidate areas, probe-then-scope method:

1. **Mob script triggers** (`mprog.mp_kill_trigger` / `mp_death_trigger` ordering
   relative to `raw_kill` and `group_gain`): read ROM C `src/fight.c:887-900` kill
   sequence, read Python `mud/combat/engine.py:_handle_death`, write one failing
   test for the ordering contract if a divergence exists.
2. **Group/follower chain** (add/remove while combat iterates `room.people`): read
   ROM C `src/fight.c:group_gain` and `src/handler.c:stop_follower`, look for
   iterator-invalidation class in Python.
3. **Position transitions under multi-attack** (victim goes DEAD mid-round via AoE):
   does Python stop further swings the way ROM does?

For each: read ROM C contract → read Python equivalent → write one failing test →
close as single-gap commit or file as INV-NNN. One probe per step, do not batch.
