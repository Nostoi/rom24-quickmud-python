# Session Status — 2026-05-25 — INV-016/HPCNT/die_follower/INV-017 (2.9.10 → 2.9.13)

## Current State

- **Active pass**: cross-file invariants + opportunistic gap closures.
  Continuation of the 2026-05-25 arc — INV-015 (2.9.7), dead-code
  sweep (2.9.8), INV-016 filed (2.9.9), INV-016 closed (2.9.10),
  HPCNT-001 closed (2.9.11), die_follower leader-chain fix (2.9.12),
  INV-017 TICK-ITERATION-SAFETY pinned (2.9.13).
- **2.9.13** — INV-017 TICK-ITERATION-SAFETY filed ✅ ENFORCED.
  ROM `src/update.c:char_update` pre-caches `ch_next` so lethal
  damage inside the per-char tick (plague/poison/incap/mortal)
  doesn't break the outer loop. Python's `for character in
  list(character_registry):` snapshot iteration enforces the same
  contract by construction. Regression test pins it down so a
  future refactor that switches to live registry iteration fails
  loudly:
  `tests/integration/test_char_update_lethal_tick_iteration.py`.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.13 |
| Tests | 4715 passed, 4 skipped, 0 failed, 0 xfailed + 1 new INV-017 test |
| Cross-file invariants | 17 of ~20 budget; INV-001 … INV-017 ✅ ENFORCED |
| Branch | `master` (2.9.10–2.9.12 on origin; 2.9.13 staged) |
| Watch list | tick iteration safety probe complete |

## Next Intended Task

INV-017 was found-and-enforced (contract already held; this is a
regression-guard pin). Remaining candidate areas from the 2026-05-25
queue:

- **Affect ticks beyond INV-015/INV-017** — `affect_update`
  per-pulse wear-off messages: verify Python's `wear_off_message`
  delivery for ROM-canonical AffectData (integer-typed) entries
  against `skill_table[paf->type].msg_off` (src/update.c:777-781).
  Tick-spell-effects only emits messages for spell_effects-managed
  entries; raw AffectData expiry routes through `affect_remove`
  silently in Python. ROM emits the msg_off line.
- **Position promotion (upward)** — `update_pos` promotes from
  STUNNED → STANDING when hp > 0 (src/handler.c:1380 ish); verify
  Python's symmetric promotion path and whether the "X stands up"
  broadcast (if any) matches ROM. INV-016 covered the downward
  direction.
- **Group XP split edge cases** — `mud/groups/xp.py:group_gain`
  vs ROM `src/fight.c:group_gain` — verify level-spread cap,
  group-skill-bonus stacking, and the "alone" branch.

Probe method (5-minute scope per AGENTS.md cross-file invariants
guidance): read ROM C contract → read Python equivalent → write
one failing test. Then either close as a single gap-closer commit
or file as the next free INV-NNN.

No push to origin without explicit per-cluster user approval.
Pending push: 2.9.13 (2.9.10–2.9.12 already on origin).
