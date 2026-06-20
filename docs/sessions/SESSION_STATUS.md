# Session Status — 2026-06-20 — INV-052 + CAST-013 + INTERP-028 (table/contract sweep)

## Current State

- **Active focus**: Systematic ROM↔Python static-table diffs + cross-file
  invariants (the per-file audit tracker is drained).
- **Last completed** (3 gaps + 1 sweep this session):
  - **INV-052** (ACT-EMPTY-DISCARD) — ROM `act_new` discards NULL/empty messages
    before delivery + TRIG_ACT; Python delivered ROM-NULL social slots (`""`) as
    blank lines. Guard added at `act_to_room` + `socials._act_to_char`.
    `social_table` (244×8) verified byte-clean.
  - **CAST-013** — `do_cast` now gates on each spell's own `minimum_position`
    (const.c-derived) instead of a flat `POS_FIGHTING`; fighting chars can no
    longer cast `POS_STANDING` utility spells. (Closed the prior #2 candidate.)
  - **INTERP-028** — removed the `bs`/`backstab` dual registration; `bs` is now a
    single hidden row → `do_backstab`, matching ROM's two cmd_table rows. Dead
    `do_bs` wrapper deleted.
  - **INV-052 follow-up sweep** — 43 direct single-recipient push sites outside
    socials audited; clean negative (all pass constant non-empty templates, or
    already guard, or route through the now-guarded `act_to_room`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-20_SOCIAL_TABLE_ACT_EMPTY_DISCARD.md](SESSION_SUMMARY_2026-06-20_SOCIAL_TABLE_ACT_EMPTY_DISCARD.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.200 |
| Tests | 6002 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Systematic table-diff gap-closing / cross-file invariants |

## Clean negatives this session (verified parity, no gap)

- `social_table` (`area/social.are` ⇄ `data/socials.json`) — full 244×8 faithful
  join, zero content diffs (only NULL-vs-`""`, neutralized by INV-052).
- Direct single-recipient push/send sites outside socials (43) — INV-052 follow-up
  sweep, all non-empty by construction.

## Next Intended Task

1. **Next table/contract probe** — pick a candidate area not yet covered by an INV
   row (affect ticks, position transitions, mob script triggers, group/follower
   chain), run a 5-minute probe (ROM C contract → Python equivalent → one failing
   test), then close as a gap or file as the next free INV-NNN.
2. **`test_all_commands.py` `tap` false-positive** — probe reports `tap` "Not
   registered" though it resolves to `sacrifice`; harness artifact, not a parity
   bug. Low priority — make the probe alias-aware if revisited.
3. **GitNexus** — MCP server disconnected late this session; run `npx gitnexus
   analyze --skip-agents-md` at next session start to refresh the graph.
4. **Risk posture**: HIGH-blast-radius behavioral logic changes → file, don't fix.
   Exception (proven 3× now — INV-052, CAST-013, INTERP-034): a change mirroring
   one ROM function/value exactly is strictly parity-correcting and safe.
