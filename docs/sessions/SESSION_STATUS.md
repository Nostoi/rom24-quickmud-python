# Session Status — 2026-06-19 — /loop gap-closer: ACT_COMM group/follow (5/5)

## Current State

- **Active focus**: Cross-file / divergence-class sweep, **Layer C** (per-file
  audit tracker exhausted). All 5 gaps this loop were **probe-surfaced** from a
  group/follow-messaging read of `src/act_comm.c` vs the Python port — same
  `act()`-render / PERS-masking / scan-domain family.
- **Last completed** (this `/loop` session, target 5/5 met, master, **push at
  end requested**):
  - `db4c5385` v2.14.144 — **GROUP-002**: charmed do_group rejection TO_VICT + `$m` pronoun.
  - `c8fabe02` v2.14.145 — **GROUP-003**: group display iterates char_list (cross-room members).
  - `2851eb15` v2.14.146 — **FOLLOW-004**: follow/unfollow TO_CHAR `$N` masks unseen master.
  - `41577401` v2.14.147 — **FOLLOW-005**: do_follow charm/NOFOLLOW rejections PERS-mask `$N`.
  - `b0b3574a` v2.14.148 — **GROUP-004**: group display uses class who_name, not "???".
  - `848517ef` — docs: filed **GROUP-005 OPEN** + corrected GROUP-003 order claim.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_GROUP_FOLLOW.md](SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_GROUP_FOLLOW.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.148 |
| Tests | 5856 passed, 4 skipped (full suite, `PYTEST_EXIT=0`, captured directly) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep (Layer C) |
| Open findings | **GROUP-005** (do_group display/broadcast PERS-masking — OPEN, ACT_COMM_C_AUDIT.md) |

## Next Intended Task

**Close `GROUP-005`** via `/rom-gap-closer` — the documented, adjacent
do_group PERS-masking gap (header/member/broadcast sites bake names instead of
ROM `PERS(x, ch)`; same bug class as FOLLOW-004/005). It's the obvious
continuation: fix shape is the existing `_pers_gated` helper (+capitalize on the
member line) and `act_format`/`act_to_room` for the broadcasts, like GROUP-002.

After GROUP-005, keep probing fresh surfaces with throwaway C-oracle-vs-pyreplay
scripts: give/put-to-mob, `do_split` gold math, weather/time, OLC. Close real
divergences via `/rom-gap-closer`; file cross-file root causes as the next
INV-NNN. **Durable lessons:** (1) never read a `pytest | tail` exit code as the
result — capture pytest's exit directly; (2) **green ≠ diff-clean** — a doubled
`extend(snapshot)` shipped past area-tests + ruff + detect_changes in `c8fabe02`,
so scan the cumulative diff before pushing. Commits db4c5385..848517ef on master.
