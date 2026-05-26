# Session Status — 2026-05-26 — INV-025 follow-up sweep complete (2.9.42)

## Current State

- **INV-025 follow-up sweep landed** across seven commits
  (`e86d55aa`..`9cbbc6b6`). ROM act() callsites now dispatch
  TRIG_ACT via `mp_act_trigger_room`: do_give (with
  `disable_mobtrigger()` wrap to mirror ROM's `MOBtrigger=FALSE`
  recursion guard), do_drop, do_get, do_put (also fixed latent
  `char.location` → `char.room` bug), do_sacrifice, equipment
  commands (wear/wield/hold/wear-all/remove), and the central
  `_broadcast_pos_change` helper used by every position transition.
- **8 new regression tests** under `tests/integration/test_inv025_*`,
  one per callsite cluster. Each test pre-installs a TRIG_ACT
  mobprog with a trigger phrase keyed to the canonical ROM message
  and asserts `mp_act_trigger` fires (or, for do_give, that
  `mp_act_trigger_room` is called but `mp_act_trigger` is suppressed
  by the wrapper).
- **INV-025 contract unchanged** — still locked at the emote site
  by the 2.9.40 enforcement test. The sweep widens coverage; it
  cannot regress what is already enforced. No new INV row.
- **INV budget unchanged at 22/~20 enforced** — sweep landed seven
  commits without filing any new INV rows.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_INV025_SWEEP.md](SESSION_SUMMARY_2026-05-26_INV025_SWEEP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.42 |
| Tests | 8/8 ✅ on new INV-025 sweep tests; broad spot-checks (give, drop, get, put, container, wear, wield, remove, equipment, hold, fight, combat, position, pos_change) all green |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **22 of ~20 enforced** — over by two, within margin per AGENTS.md soft cap |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.42 commit pending push approval |

## Next Intended Task

1. **Continue probe-then-scope** at the 22/~20 budget. Methodology
   is still earning its keep — recent passes have closed real
   contracts without inflating the count.
2. **Latent `char.location` audit** (low priority follow-up): grep
   for other `getattr(char, "location", ...)` callsites — `do_put`
   was reading the wrong attribute and silently dropping its
   TO_ROOM broadcasts. One spot in `do_quaff` uses
   `char.room or char.location` (harmless because `char.room`
   wins); one in `_perform_remove` was a similar harmless fallback.
   Worth a 10-minute sweep to make sure no other call silently
   no-ops.
3. **Future consolidation candidates** (don't merge yet):
   INV-016 / INV-019 (position-transition broadcast / silent
   promotion-on-heal duals on `update_pos`); INV-006 / INV-009
   (fighting-pointer coherence after death / registry-disconnect
   cleanup on `character_registry` membership transitions). Either
   would free one slot if the budget creeps back above 25.

GitNexus index is stale at `c75f898` (seven sweep commits postdate
it). Refresh with `npx gitnexus analyze --skip-agents-md` before the
next probe so impact-analysis numbers are accurate.
