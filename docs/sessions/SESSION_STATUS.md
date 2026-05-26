# Session Status — 2026-05-25 → 26 — INV-016 → do_follow notify (2.9.10 → 2.9.19)

## Current State

- **Active pass**: cross-file invariants + opportunistic gap closures.
  Ten clusters landed this session: INV-016 (2.9.10), HPCNT-001 (2.9.11),
  die_follower (2.9.12), INV-017 (2.9.13), INV-018 (2.9.14),
  group XP NPC level-1 floor (2.9.15), INV-019 (2.9.16),
  do_say/do_tell SPEECH gate (2.9.17),
  do_buy TO_ROOM broadcast (2.9.18),
  do_follow add/stop notify broadcasts (2.9.19).
- **2.9.19** — `mud/commands/group_commands.py:add_follower` and
  `stop_follower` (the variants the command dispatcher uses) were
  silent. ROM `src/act_comm.c:1602-1605, 1626-1630` emits
  `$n now follows you.` / `You now follow $N.` and the symmetric
  stop pair. Surfaced a parallel divergence: a second canonical copy
  in `mud/characters/follow.py` already had the broadcasts but is
  not the wired one. Duplicate-implementations sweep deferred.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.19 |
| Tests | 4732 passed, 4 skipped (full suite, 9m32s) |
| Cross-file invariants | 19 of ~20 budget; INV-001 … INV-019 ✅ ENFORCED |
| Branch | `master` (2.9.10–2.9.18 on origin; 2.9.19 staged) |
| Watch list | follow/group probe ✅ (gap closed, not INV) |

## Next Intended Task

The do_follow probe surfaced a deeper duplicate-implementation
issue: `add_follower` / `stop_follower` / `is_same_group` exist in
both `mud/characters/follow.py` (canonical, used by combat death) and
`mud/commands/group_commands.py` (used by command dispatcher).
This is itself a divergence trap — they will drift. A consolidation
session should remove the group_commands copies and have do_follow
call the canonical variants. Out of scope for a single gap-closer.

Candidate areas for next probe (19/~20 INV budget):

1. **Duplicate-follow-impl consolidation** — merge group_commands
   `add_follower`/`stop_follower`/`is_same_group` into the
   `mud/characters/` canonical module. Multi-test, multi-file —
   likely needs its own session or a small audit.
2. **INV-budget restructuring** — at 19/~20, AGENTS.md notes
   reviewing the invariant taxonomy. Skim the per-file audit tracker
   for rows that should be lifted to INV.
3. **`do_value` price reporting** — ROM `src/act_obj.c:2965` —
   `act("$n tells you 'I'll give you N coins for $p'.", ...)`.
   Probe whether Python emits TO_VICT vs TO_CHAR correctly.
4. **`do_group`** — ROM `src/act_comm.c:1770-1850` — adding
   someone to a group sets `victim->leader = ch`. Probe whether
   `is_same_group` matches ROM after a `group X` command.

Probe method: read ROM C contract → read Python equivalent → write
one failing test. Then close as single gap-closer or file INV-020.

No push to origin without explicit per-cluster user approval.
Pending push: 2.9.19.
