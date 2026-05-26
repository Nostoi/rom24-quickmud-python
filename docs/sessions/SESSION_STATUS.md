# Session Status — 2026-05-25 — INV-016 → do_buy TO_ROOM broadcast (2.9.10 → 2.9.18)

## Current State

- **Active pass**: cross-file invariants + opportunistic gap closures.
  Nine clusters landed today: INV-016 (2.9.10), HPCNT-001 (2.9.11),
  die_follower (2.9.12), INV-017 (2.9.13), INV-018 (2.9.14),
  group XP NPC level-1 floor (2.9.15), INV-019 (2.9.16),
  do_say/do_tell `!IS_NPC(ch)` SPEECH gate (2.9.17),
  do_buy `$n buys $p.` TO_ROOM broadcast (2.9.18).
- **2.9.18** — `do_buy` was missing the ROM `$n buys $p[N].` /
  `$n buys $p.` TO_ROOM broadcast (`src/act_obj.c:2734-2745`).
  Sibling `do_sell` already had the matching `$n sells $p.`
  broadcast; this aligns the buy side. Two enforcement tests in
  `tests/integration/test_shop_room_broadcasts.py` (one pins do_buy,
  one regression-pins do_sell).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.18 |
| Tests | 4731 passed, 4 skipped (full suite, 8m47s) |
| Cross-file invariants | 19 of ~20 budget; INV-001 … INV-019 ✅ ENFORCED |
| Branch | `master` (2.9.10–2.9.17 on origin; 2.9.18 staged) |
| Watch list | shop atomicity probe ✅ (gap closed, not INV) |

## Next Intended Task

Shop probe was a clean single-file gap (no INV needed). Remaining
candidate areas before INV-budget restructuring (19/~20):

1. **Group/follower auto-assist edges not covered by die_follower
   (2.9.12)** — when leader changes via `do_follow`, does
   `is_same_group` membership update everywhere it needs to?
2. **INV-budget restructuring discussion** — at 19/~20, AGENTS.md
   notes this is the threshold for reviewing the invariant taxonomy.
   Worth re-skimming the per-file audit tracker for rows that
   should be lifted to INV status.
3. **Other shop transaction edges** — `do_value` price reporting,
   pet shop atomicity, ROM `obj_to_keeper` dedup contract.

Probe method (5-minute scope): read ROM C contract → read Python
equivalent → write one failing test. Then close as a single
gap-closer commit or file as the next free INV-NNN.

No push to origin without explicit per-cluster user approval.
Pending push: 2.9.18.
