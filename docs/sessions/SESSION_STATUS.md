# Session Status — 2026-05-25 — INV-016 + HPCNT-001 + die_follower (2.9.10 → 2.9.12)

## Current State

- **Active pass**: cross-file invariants + opportunistic gap closures.
  Continuation of the 2026-05-25 arc — INV-015 (2.9.7), dead-code
  sweep (2.9.8), INV-016 filed (2.9.9), INV-016 closed (2.9.10),
  HPCNT-001 closed (2.9.11), `die_follower` leader-chain fix (2.9.12).
- **2.9.10** — INV-016 BCAST-ON-POSITION-TRANSITION closed
  (✅ ENFORCED). `mud/combat/engine.py:apply_position_change`
  extracted as the shared enforcement point; wired into 16
  damage-spell sites in `mud/skills/handlers.py`. Commit `589aada`.
- **2.9.11** — HPCNT-001 closed. Spurious `mp_hprct_trigger`
  block removed from `_apply_damage`; canonical site at end of
  `multi_hit` (NPC attacker only) preserved. Two enforcement tests
  in `tests/integration/test_hpcnt_once_per_pulse.py`. Commit `4c8cec0`.
- **2.9.12** — Group/follower probe surfaced `die_follower`
  divergence vs ROM `src/act_comm.c:1658-1680`. Python missed
  self-detach from master (+ master.pet clear), self-leader clear,
  and the **leader-chain reset** (`fch->leader = fch` for every
  follower whose leader was the deceased — NOT NULL, since
  `is_same_group` walks leader pointers and dangling pointers at
  an extracted corpse would still equate unrelated survivors).
  Fix in `mud/characters/follow.py:die_follower` mirrors ROM
  exactly. Two enforcement tests in
  `tests/integration/test_die_follower_leader_chain.py`.
- **Last completed**: 2.9.12 staged locally (uncommitted at the
  moment SESSION_STATUS is written; commit pending suite green).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-25_INV016_POSITION_TRANSITION_BROADCAST.md](SESSION_SUMMARY_2026-05-25_INV016_POSITION_TRANSITION_BROADCAST.md) (covers INV-016; HPCNT-001 and die_follower are CHANGELOG-only).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.12 |
| Tests | suite running; 2 new die_follower tests + the 4717 baseline |
| Cross-file invariants | 16 of ~20 budget; INV-001 … INV-016 ✅ ENFORCED |
| Branch | `master` (2.9.10–2.9.11 local; 2.9.12 staged; 2.9.7–2.9.9 on origin) |
| Watch list | mob script trigger probe complete; group/follower probe complete (HPCNT-001 + die_follower closed) |

## Next Intended Task

The mob-script-trigger and group/follower probes are both complete.
Remaining candidate areas from the 2026-05-25 prompt queue that
have not yet been probed:

- **Affect ticks** beyond INV-015 — `affect_update` at
  `src/update.c:762-786` runs once per pulse on every char; verify
  Python's per-char iteration order, char-death-during-iteration
  safety, and the `wear_off_message` delivery path against ROM.
- **Position transitions** beyond INV-016 — verify the
  STUNNED → STANDING auto-stand from `mud/combat/engine.py:update_pos`
  (src/fight.c:805-826) versus the upward heal-driven path
  (cure_*/heal); ROM does NOT broadcast on upward transitions but
  does promote position automatically when hit > 0 from
  `STUNNED/MORTAL/INCAP`. Quick scan for whether Python promotes
  symmetrically.
- **Group XP split edge cases** — `mud/groups/xp.py:group_gain`
  vs ROM `src/fight.c:group_gain` — verify level-spread cap,
  group-skill-bonus stacking with class-skill bonuses, and the
  "alone" branch (single-member group still gets full XP).

Probe method (5-minute scope per AGENTS.md cross-file invariants
guidance): read ROM C contract → read Python equivalent → write
one failing test. Then either close as a single gap-closer commit
or file as the next free INV-NNN.

No push to origin without explicit per-cluster user approval.
Pending push: 2.9.10, 2.9.11, 2.9.12 (commit pending).
