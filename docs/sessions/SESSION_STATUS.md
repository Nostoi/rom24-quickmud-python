# Session Status — 2026-05-25 — INV-016 → SPEECH-trigger gate (2.9.10 → 2.9.17)

## Current State

- **Active pass**: cross-file invariants + opportunistic gap closures.
  Eight clusters landed today: INV-016 (2.9.10), HPCNT-001 (2.9.11),
  die_follower (2.9.12), INV-017 (2.9.13), INV-018 (2.9.14),
  group XP NPC level-1 floor (2.9.15), INV-019 (2.9.16),
  do_say/do_tell `!IS_NPC(ch)` SPEECH gate (2.9.17).
- **2.9.17** — `do_say` and `do_tell` were missing ROM's
  `!IS_NPC(ch)` gate on the SPEECH listener loop
  (`src/act_comm.c:779` and `:946`). The gate prevents mob-to-mob
  speech-trigger cascades (mob A says X → mob B's SPEECH fires →
  triggers another say → loop). Single-file fix in
  `mud/commands/communication.py`. Two enforcement tests in
  `tests/integration/test_npc_speaker_does_not_trigger_speech.py`.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.17 |
| Tests | 4727+ baseline + 2 new (NPC-speaker gate) |
| Cross-file invariants | 19 of ~20 budget; INV-001 … INV-019 ✅ ENFORCED |
| Branch | `master` (2.9.10–2.9.16 on origin; 2.9.17 staged) |
| Watch list | mob script triggers probe ✅ (gap closed, not INV) |

## Next Intended Task

The mob-trigger probe was successful — found and closed a real
single-file gap rather than filing a new INV. Surfaces still probed
and clean: GIVE/BRIBE trigger paths (`mud/commands/give.py`), GREET
trigger paths (`mud/world/movement.py:move_character` +
`move_character_through_portal`).

Remaining candidate areas before INV-budget restructuring (19/~20):

1. **Shop transaction atomicity** — `mud/commands/shop.py:do_buy` /
   `do_sell` / `do_list` / `do_value`. ROM `src/act_obj.c` shop
   block. Probe whether `obj_to_char` + cost deduction is atomic
   under any inventory-bound or carry-weight short-circuit.
2. **Group/follower auto-assist edges not covered by die_follower
   (2.9.12)** — when leader changes via `do_follow`, does
   `is_same_group` membership update everywhere it needs to?
3. **INV-budget restructuring discussion** — at 19/~20, AGENTS.md
   notes this is the threshold for reviewing the invariant taxonomy.
   Worth re-skimming the per-file audit tracker for rows that
   should be lifted to INV status.

Probe method (5-minute scope): read ROM C contract → read Python
equivalent → write one failing test. Then close as a single
gap-closer commit or file as the next free INV-NNN.

No push to origin without explicit per-cluster user approval.
Pending push: 2.9.17.
