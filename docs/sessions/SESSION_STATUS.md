# Session Status — 2026-05-25 — INV-016 → group XP NPC-level floor (2.9.10 → 2.9.15)

## Current State

- **Active pass**: cross-file invariants + opportunistic gap closures.
  Six clusters landed today: INV-016 (2.9.10), HPCNT-001 (2.9.11),
  die_follower (2.9.12), INV-017 (2.9.13), INV-018 (2.9.14),
  group XP NPC level-1 floor (2.9.15).
- **2.9.15** — Group XP gap closer. `mud/groups/xp.py:group_gain`
  was flooring NPC level contributions at 1 (`max(1, level // 2)`)
  instead of ROM's raw `level / 2`. At NPC level 1 this inflated
  `total_levels` by 1, and the share-formula denominator
  `max(1, total_levels - 1)` by 1, reducing the PC's XP award by
  ~10% on charmed-pet groups. Single-file fix; not cross-module,
  no INV row. Two enforcement tests in
  `tests/integration/test_group_xp_npc_level_floor.py`.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.15 |
| Tests | 4718+ baseline + 2 new (group XP enforcement) |
| Cross-file invariants | 18 of ~20 budget; INV-001 … INV-018 ✅ ENFORCED |
| Branch | `master` (2.9.10–2.9.14 on origin; 2.9.15 staged) |
| Watch list | wear-off probe ✅, group XP probe ✅, position-promotion remains |

## Next Intended Task

The group XP probe is complete with one fix landed; remaining
candidate from the queue:

- **Position promotion (upward)** — `update_pos` promotes from
  STUNNED → STANDING when hp > 0; verify Python's symmetric
  promotion path matches ROM. INV-016 covered the downward
  broadcast direction (which goes through `damage()`); the upward
  promotion happens from heal paths and natural HP regen. The
  question is whether Python promotes symmetrically (no broadcast,
  just position update) and whether the auto-stand from
  STUNNED → RESTING/STANDING fires at the right HP threshold.

Per AGENTS.md cross-file invariants budget note: tracker is at
18 of ~20. If the position-promotion probe surfaces a contract
that crosses modules, file as INV-019 — one slot before discussing
budget restructuring before INV-021.

Probe method (5-minute scope): read ROM C contract → read Python
equivalent → write one failing test. Then close as a single
gap-closer commit or file as the next free INV-NNN.

No push to origin without explicit per-cluster user approval.
Pending push: 2.9.15.
