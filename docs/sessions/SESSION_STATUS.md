# Session Status — 2026-06-20 — interp.c cmd_table + skill_table data sweep (/loop)

## Current State

- **Active focus**: Systematic ROM↔Python static-table diffs (the per-file audit
  tracker is drained; this is the cross-file / divergence-class pass). This `/loop`
  session swept `src/interp.c`'s `cmd_table` across **every field** and diffed
  `src/const.c`'s `skill_table`.
- **Last completed**: 9 parity gaps — **INTERP-027/029/030/031/032/033/034** (entire
  `interp.c` cmd_table now has a parametrized anti-drift guard per field: trust=001,
  position=030+singles, show=032, log=033, consumer=034) and **CONST-008/009**
  (skill_table: cancellation target + cancellation/harm uncastable). Plus a
  determinism flake fix and an INTERP-034 follow-up test correction. **2 SECURITY
  fixes** (INTERP-033/034: password command no longer logged).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-20_INTERP_CMDTABLE_AND_SKILL_DATA.md](SESSION_SUMMARY_2026-06-20_INTERP_CMDTABLE_AND_SKILL_DATA.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.197 |
| Tests | 5984 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Systematic table-diff gap-closing / cross-file invariants |

## Clean negatives this session (verified parity, no gap)

`skill_table` (mana/beats/targets/levels/ratings/slot — 135 skills, full join, after
CONST-008/009), `liq_table`, `pc_race_table`, `class_table`, `mob_cmd_table`.

## Next Intended Task

The low-risk data/registration veins are now drained (interp cmd_table fully swept;
all checked const.c static tables clean). Remaining candidates, in priority order:

1. **`social_table` diff** — `area/social.are` ⇄ `data/socials.json`. Counts match
   (244) but needs the **existing `mud/loaders/social_loader.py`** to parse (the .are
   format has variable-length records with `#` terminators; a naive line-parser is
   wrong). Status this session: INCONCLUSIVE — neither clean nor buggy established.
2. **INTERP-028** (OPEN, MINOR) — duplicate `bs` registration; cosmetic, no
   observable divergence.
3. **Per-spell `min_position` enforcement** (behavioral, verify-then-decide) — ROM
   skill_table carries a POS per spell; `do_cast` gates on a flat `POS_FIGHTING`.
   Whether Python should enforce each spell's own min position is unverified.
4. **Risk posture (advisor)**: when a behavioral divergence needs logic changes in a
   HIGH-blast-radius core path (combat/movement/dispatch), **file it**, do not fix
   autonomously — leave for human-reviewed work.
