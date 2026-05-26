# Session Status — 2026-05-25 — INV-016/HPCNT/die_follower/INV-017/INV-018 (2.9.10 → 2.9.14)

## Current State

- **Active pass**: cross-file invariants. Continuation of 2026-05-25 arc.
  Five clusters landed today: INV-016 closed (2.9.10), HPCNT-001
  closed (2.9.11), die_follower leader-chain fix (2.9.12),
  INV-017 TICK-ITERATION-SAFETY pinned (2.9.13), INV-018
  WEAR-OFF-MESSAGE-FOR-RAW-AFFECT closed (2.9.14).
- **2.9.14** — INV-018 closed (✅ ENFORCED). ROM
  `src/update.c:777-781` emits `skill_table[paf->type].msg_off` on
  any positive-typed affect expiry; Python `tick_spell_effects`
  was only emitting wear-off for spell_effects-shadowed entries,
  silently expiring raw `AffectData` (the plague-spread path at
  `mud/game_loop.py:614-624` is the production trigger). Fix:
  `mud/affects/engine.py:_lookup_raw_affect_wear_off` mirrors the
  precedent at `_broadcast_object_wear_off` — explicit
  `wear_off_message` attribute first, then `skill_registry` fallback
  by spell name. Two enforcement tests in
  `tests/integration/test_inv018_wear_off_message_for_raw_affect.py`.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.14 |
| Tests | 4715+ baseline + 5 new (INV-016, INV-017, INV-018x2, HPCNT-001x2, die_followerx2 net adds) |
| Cross-file invariants | 18 of ~20 budget; INV-001 … INV-018 ✅ ENFORCED |
| Branch | `master` (2.9.10–2.9.13 on origin; 2.9.14 staged) |
| Watch list | wear-off probe complete; one remaining INV slot before tracker budget |

## Next Intended Task

INV tracker is now at 18 of ~20. Two remaining candidates from the
queue:

- **Position promotion (upward)** — `update_pos` promotes from
  STUNNED → STANDING when hp > 0; verify Python's symmetric
  promotion path matches ROM. INV-016 covered the downward
  broadcast direction.
- **Group XP split edge cases** — `mud/groups/xp.py:group_gain`
  vs ROM `src/fight.c:group_gain`. Verify level-spread cap,
  group-skill-bonus stacking, and the "alone" branch.

Per AGENTS.md cross-file invariants budget note: "If it grows past
~20 invariants, something has gone wrong with the per-file audit
methodology and the two trackers should be merged or restructured.
Discuss before adding INV-021." We have headroom for two more
probes before re-evaluating the methodology.

Probe method (5-minute scope): read ROM C contract → read Python
equivalent → write one failing test. Then close as a single
gap-closer commit or file as the next free INV-NNN.

No push to origin without explicit per-cluster user approval.
Pending push: 2.9.14.
