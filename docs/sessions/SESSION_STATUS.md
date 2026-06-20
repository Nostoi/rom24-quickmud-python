# Session Status — 2026-06-20 — social_table diff + INV-052 (act_new empty-discard)

## Current State

- **Active focus**: Systematic ROM↔Python static-table diffs + cross-file
  invariants (the per-file audit tracker is drained). This session resolved the
  prior session's #1 open item — the `social_table` diff.
- **Last completed**: **INV-052** (ACT-EMPTY-DISCARD) — ROM `act_new` discards
  NULL/empty messages before delivery + TRIG_ACT dispatch; Python delivered
  ROM-NULL social slots (stored as `""`) as spurious blank lines. Closed with an
  `act_new`-faithful empty-guard at `act_to_room` + `socials._act_to_char`. The
  `social_table` (244 socials × 8 fields) is otherwise **byte-clean** — verified
  by a full faithful `load_socials`/`fread_string_eol` replay join.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-20_SOCIAL_TABLE_ACT_EMPTY_DISCARD.md](SESSION_SUMMARY_2026-06-20_SOCIAL_TABLE_ACT_EMPTY_DISCARD.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.198 |
| Tests | 5988 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Systematic table-diff gap-closing / cross-file invariants |

## Clean negatives this session (verified parity, no gap)

`social_table` (`area/social.are` ⇄ `data/socials.json`) — full 244-social ×
8-field faithful join: no missing/extra socials, no dups, zero content diffs. The
only divergence was NULL-vs-`""` representation, neutralized by INV-052.

## Next Intended Task

The low-risk data/registration veins are drained. Remaining candidates, priority
order:

1. **INTERP-028** (OPEN, MINOR) — duplicate `bs` registration; cosmetic, no
   observable divergence.
2. **Per-spell `min_position` enforcement** (behavioral, verify-then-decide) — ROM
   `skill_table` carries a POS per spell; `do_cast` gates on a flat
   `POS_FIGHTING`; `skills.json` carries no per-spell POS. Whether Python should
   enforce each spell's own min position is unverified. **HIGH-blast-radius core
   path (do_cast/dispatch) → FILE, do not fix autonomously.**
3. **INV-052 follow-up (low-yield)** — general sweep of direct single-recipient
   `push_message`/`send_to_char_buffered` empty-variable sites outside socials.
   Re-open per-site only if a scenario/golden surfaces a blank-line leak.
4. **Risk posture (advisor)**: HIGH-blast-radius behavioral logic changes →
   file, don't fix. Exception: pure additive guards mirroring one ROM function
   exactly (INV-052 / INTERP-034) are strictly parity-correcting and safe.
