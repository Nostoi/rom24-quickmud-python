# Session Status — 2026-05-25 — INV-016 closure + HPCNT-001 (2.9.10 → 2.9.11)

## Current State

- **Active pass**: cross-file invariants + opportunistic gap closures.
  Continuation of the 2026-05-25 arc — INV-015 (2.9.7), dead-code
  sweep (2.9.8), INV-016 filed (2.9.9), INV-016 closed (2.9.10),
  HPCNT-001 closed (2.9.11).
- **2.9.10** — INV-016 BCAST-ON-POSITION-TRANSITION closed
  (✅ ENFORCED). `mud/combat/engine.py:apply_position_change`
  extracted as the shared enforcement point; wired into the 16
  damage-spell sites in `mud/skills/handlers.py` that bypass
  `apply_damage`. Commit `589aada`.
- **2.9.11** — HPCNT-001 closed. ROM `src/fight.c:97` fires
  `mp_hprct_trigger` exactly once per violence pulse per NPC
  (`violence_update` → `multi_hit` → end-of-multi_hit firing on
  the NPC attacker). Python's `mud/combat/engine.py:_apply_damage`
  carried a spurious extra firing on the NPC victim per damage
  application (with a misattributed ROM ref comment) — every NPC
  taking damage fired HPCNT N+1 times per `multi_hit`, plus it
  fired on spell-damage paths where ROM doesn't fire HPCNT at all.
  Block deleted. Two enforcement tests in
  `tests/integration/test_hpcnt_once_per_pulse.py`.
- **Last completed**: working tree at 2.9.11 (HPCNT-001 uncommitted; 2.9.10 committed at `589aada`).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-25_INV016_POSITION_TRANSITION_BROADCAST.md](SESSION_SUMMARY_2026-05-25_INV016_POSITION_TRANSITION_BROADCAST.md) (covers INV-016; HPCNT-001 is CHANGELOG-only).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.11 |
| Tests | 4717 passed, 4 skipped, 0 failed, 0 xfailed (4715 + 2 new HPCNT enforcement) |
| Cross-file invariants | 16 of ~20 budget; INV-001 … INV-016 ✅ ENFORCED |
| Branch | `master` (2.9.10 committed local `589aada`; 2.9.11 uncommitted; 2.9.7–2.9.9 on origin) |
| Watch list | group/follower chain (unprobed) |

## Next Intended Task

The per-file audit tracker is exhausted and the cross-file
invariants tracker is now fully ✅ at 16/~20. The mob-script-trigger probe surfaced HPCNT-001 (closed in 2.9.11);
the remaining trigger sites (ENTRY/GREET/GIVE/BRIBE/EXIT/FIGHT/KILL/
DEATH/RANDOM/DELAY/SPEECH/ACT) all match ROM contracts on second
read. Mob-script-trigger probe declared complete.

Next candidate from the 2026-05-25 prompt's queue:

- **Group / follower chain** — leader/master pointers, group XP
  split, follow propagation, disband-on-death. Probe-then-scope as
  usual: ROM `src/handler.c:is_same_group` / `src/fight.c:group_gain`
  / `src/act_comm.c:do_group` / `src/handler.c:add_follower` /
  `stop_follower` against the Python `mud/characters/follow.py` +
  `mud/characters/groups` surface. Likely INV-017 territory if a
  contract divergence surfaces.

Probe method (5-minute scope, per AGENTS.md cross-file invariants
guidance): read the ROM C contract → read the Python equivalent →
write one failing test. Then either close as a single gap-closer
commit, or file as the next free INV-NNN with a documenting
xfail-strict test if closure spans multiple modules.

No push to origin without explicit per-cluster user approval.
