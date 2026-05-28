# Session Status — 2026-05-28 — FIGHT-019 combat THAC0 hit model (FINDING-008 sub-issue 1)

## Current State

- **Active mode**: differential-harness-driven parity verification. The harness
  surfaced FINDING-008 (combat first-attack divergence at `kill drunk`); this
  session triaged all three sub-issues and closed the one real engine parity bug.
- **Last completed**:
  - **`FIGHT-019`** ✅ FIXED (master 2.11.4, `7f4d55f1`) — combat now uses ROM's
    THAC0 / `number_bits(5)` hit model exclusively; the non-ROM percent model and
    the `COMBAT_USE_THAC0` flag are deleted. Also fixed a second masked divergence:
    the NPC-attacker THAC0 branch (ROM `src/fight.c:445-457` — `thac0_00=20`,
    `thac0_32` from ACT class flag). 15 percent-model-dependent combat tests
    re-baselined; a `test_room` isolation leak fixed.
  - **FINDING-008 triage (durable)**: sub-issue 1 = real bug, fixed via FIGHT-019;
    sub-issue 2 (color codes) = harness color-normalization; sub-issue 3
    (double-delivery) = **harness capture artifact, NOT a SINGLE-DELIVERY
    violation** (isolated `multi_hit` returns one line). #2/#3 remain harness-side
    on `diff-harness`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_FIGHT_019_THAC0_HIT_MODEL.md](SESSION_SUMMARY_2026-05-28_FIGHT_019_THAC0_HIT_MODEL.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-28_SPAWN_001_RNG_DRAW_ORDER.md](SESSION_SUMMARY_2026-05-28_SPAWN_001_RNG_DRAW_ORDER.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version (master) | **2.11.4** (unpushed; `diff-harness` separate, unmerged) |
| Tests (master) | **4928 passed, 4 skipped, 0 failed** (full parallel suite, post-FIGHT-019). |
| ROM C files audited | 40 / 43 ✅ (3 N/A). `fight.c` `one_hit` row corrected — FIGHT-019 closed the hit-model divergence the per-file audit had certified at 95%. |
| Differential harness | **Sound.** Has caught **8 issues** (FINDING-001→008). FINDING-008 sub-issue 1 resolved via FIGHT-019; sub-issues 2 (color norm) + 3 (capture double-count) remain harness-side. `combat_melee_rounds` xfail correctly stays red until #2/#3 reconcile. v1 on `diff-harness`, unmerged. |
| Branch | `master` — **2 commits ahead of `origin`, UNPUSHED** (SPAWN-001 `47f8fd75` + FIGHT-019 `7f4d55f1`). Push blocked on 10 pre-existing ruff I001 errors in `templates.py`. `diff-harness` — local-only, FINDING-008 #2/#3 open. |

## Next Intended Task

1. **Triage FINDING-008 sub-issues 2/3 on `diff-harness`** — color normalization
   (`compare._norm_lines`) and the replay capture double-count — so the
   `combat_melee_rounds` differential goes clean and combat v1 can land. Triage
   conclusions already recorded in the latest summary + `FINDING-008`.
2. **Settle the pre-existing `templates.py` ruff I001 errors** (`--fix`-able),
   then push `master` (SPAWN-001 + FIGHT-019).
3. **Merge `diff-harness` → master** once combat v1 is green.
4. **Combat-test brittleness hardening pass** — pin `number_bits` in the unseeded
   `tests/test_combat.py` hit/damage tests (see Notes in `FIGHT_C_AUDIT.md`).
5. **INV-025 non-combat narration sweep** — still open from earlier.
