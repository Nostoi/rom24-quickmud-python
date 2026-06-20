# Session Status — 2026-06-20 — social_table/INV-052 + CAST-013 (per-spell min position)

## Current State

- **Active focus**: Systematic ROM↔Python static-table diffs + cross-file
  invariants (the per-file audit tracker is drained).
- **Last completed**:
  - **INV-052** (ACT-EMPTY-DISCARD) — ROM `act_new` discards NULL/empty messages
    before delivery + TRIG_ACT dispatch; Python delivered ROM-NULL social slots
    (stored as `""`) as spurious blank lines. Closed with an `act_new`-faithful
    empty-guard at `act_to_room` + `socials._act_to_char`. `social_table`
    (244×8) verified **byte-clean** by a faithful `load_socials` replay join.
  - **CAST-013** — `do_cast` gated on a flat `POS_FIGHTING` for every spell
    instead of each spell's own `minimum_position` (ROM `src/magic.c:341`). A
    fighting char could cast `POS_STANDING` utility spells ROM blocks with "You
    can't concentrate enough." Fixed via a const.c-derived per-spell position
    map; offensive spells unaffected. **This closes the prior SESSION_STATUS
    candidate #2** (was tagged "HIGH-blast-radius → FILE, do not fix"; the user
    authorized the fix and it is strictly parity-correcting).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-20_SOCIAL_TABLE_ACT_EMPTY_DISCARD.md](SESSION_SUMMARY_2026-06-20_SOCIAL_TABLE_ACT_EMPTY_DISCARD.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.199 |
| Tests | 5992 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Systematic table-diff gap-closing / cross-file invariants |

## Clean negatives this session (verified parity, no gap)

`social_table` (`area/social.are` ⇄ `data/socials.json`) — full 244-social ×
8-field faithful join: no missing/extra socials, no dups, zero content diffs (only
NULL-vs-`""` representation, neutralized by INV-052).

## Next Intended Task

Remaining candidates, priority order:

1. **INTERP-028** (OPEN, MINOR) — duplicate `bs` registration; cosmetic, no
   observable divergence.
2. **INV-052 follow-up (low-yield)** — general sweep of direct single-recipient
   `push_message`/`send_to_char_buffered` empty-variable sites outside socials.
   Re-open per-site only if a scenario/golden surfaces a blank-line leak.
3. **Next table/contract probe** — pick a candidate area not yet covered by an INV
   row (affect ticks, position transitions, mob script triggers, group/follower
   chain), run a 5-minute probe (ROM C contract → Python equivalent → one failing
   test), then close as a gap or file as the next free INV-NNN.
4. **Risk posture**: HIGH-blast-radius behavioral logic changes → file, don't fix.
   Exception (proven twice now — INV-052, CAST-013): a change that mirrors one ROM
   function/value exactly is strictly parity-correcting and safe despite a wide
   caller count.
