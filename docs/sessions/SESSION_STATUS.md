# Session Status — 2026-05-25 — INV-016 BCAST-ON-POSITION-TRANSITION closed (2.9.10)

## Current State

- **Active pass**: cross-file invariants. Continuation of the
  2026-05-25 arc — INV-015 (2.9.7), dead-code sweep (2.9.8),
  INV-016 filed (2.9.9), and now INV-016 closed (2.9.10).
- **2.9.10** — INV-016 BCAST-ON-POSITION-TRANSITION closed
  (✅ ENFORCED). Extracted
  `mud/combat/engine.py:apply_position_change(victim, old_pos)`
  as the shared enforcement point and wired it into the 16
  damage-spell sites in `mud/skills/handlers.py` that bypass
  `apply_damage`. Heals correctly skip the helper. The xfail
  documenting test in
  `tests/integration/test_inv016_position_transition_broadcast.py`
  was flipped to passing strict-fail (assertion adapted from INCAP
  to DEAD to match the level-30 / 1-hp fixture's `acid_blast`
  damage range — same invariant, different threshold).
- **Last completed**: working tree at 2.9.10 (uncommitted).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-25_INV016_POSITION_TRANSITION_BROADCAST.md](SESSION_SUMMARY_2026-05-25_INV016_POSITION_TRANSITION_BROADCAST.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.10 |
| Tests | 4715 passed, 4 skipped, 0 failed, 0 xfailed |
| Cross-file invariants | 16 of ~20 budget; INV-001 … INV-016 ✅ ENFORCED |
| Branch | `master` (working tree uncommitted; 2.9.7–2.9.9 already on origin) |
| Watch list | mob script triggers, group/follower chain (unprobed) |

## Next Intended Task

The per-file audit tracker is exhausted and the cross-file
invariants tracker is now fully ✅ at 16/~20. Next candidates from
the 2026-05-25 prompt's queue:

1. **Mob script triggers** — ENTRY / GIVE / KILL / RANDOM / HPCNT
   firing across `mob_cmds`, `game_loop`, `handler`, `dispatcher`.
   Likely INV-017 territory if a contract divergence surfaces.
2. **Group / follower chain** — leader/master pointers, group XP
   split, follow propagation, disband-on-death.

Probe method (5-minute scope, per AGENTS.md cross-file invariants
guidance): read the ROM C contract → read the Python equivalent →
write one failing test. Then either close as a single gap-closer
commit, or file as the next free INV-NNN with a documenting
xfail-strict test if closure spans multiple modules.

No push to origin without explicit per-cluster user approval.
