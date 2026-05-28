# Session Status — 2026-05-27 — INV-028 light-slot coherence + stale-test cleanup (2.9.86)

## Current State

- **Last completed**: **INV-028 (LIGHT-SLOT-KEY-COHERENCE)** ✅ ENFORCED (2.9.85)
  — `do_wear`/`do_hold` now route `ITEM_LIGHT` into `WearLocation.LIGHT`
  (ROM `act_obj.c:1415-1422`), and both readers (`Room._has_lit_light_source`,
  `_find_equipped_light`) tolerate the live-int and reloaded-str key forms.
  This also activates the 2.9.81 ARITH-202 burnout fix in live play. Then
  fixed **5 stale stat-floor unit tests** (2.9.86) left behind by ARITH-105's
  floor-3 change, surfaced by the first full-suite run this work stream.
- **Active audit**: META Class 2 ARITHMETIC_BOUNDARY close-out — **21 FIXED /
  19 N/A / 7 ❌ MISSING** (unchanged this session; INV-028 is a cross-file
  invariant, not an ARITH row).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_INV_028_LIGHT_SLOT.md](SESSION_SUMMARY_2026-05-27_INV_028_LIGHT_SLOT.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_ARITH_202_205_CLOSE.md](SESSION_SUMMARY_2026-05-27_ARITH_202_205_CLOSE.md),
  [SESSION_SUMMARY_2026-05-27_GL_024_LEVEL1_PLAGUE.md](SESSION_SUMMARY_2026-05-27_GL_024_LEVEL1_PLAGUE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.86 |
| Tests | **Full suite: 4889 passed, 4 skipped, 0 failed** in 486s. INV-028 suite 3/3; the 5 prior stat-floor unit failures resolved. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75%. |
| Cross-file invariants | **24 ENFORCED** (INV-028 added) + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE). |
| Meta-audit progress | 6 of 8 META classes complete/triaged. ARITHMETIC_BOUNDARY: 21 FIXED / 19 N/A / 7 ❌ MISSING. |
| Branch | `master` — local 2.9.86 ahead of `origin/master` by **9 commits** (GL-024 2.9.80 → INV-028 2.9.85 → stale-tests 2.9.86). Handoff commit makes 10. (2.9.77→2.9.79 already pushed.) |

## Next Intended Task

1. **Push approval** — 9 (soon 10) commits ahead of `origin/master`, shipping
   2.9.80 → 2.9.86. Verify with `git log origin/master..HEAD`. Not pushed.
2. **Equipment-dict key-type normalization** (INV-028 followup) — live `int`
   vs reloaded `str` slot keys affect every slot, not just LIGHT. Normalize on
   load (coerce to `int(wear_loc)` in persistence restore) and drop the
   per-reader tolerance shims. Candidate INV / persistence gap.
3. **`_wear_all` light handling** — `wear all` won't equip a light (no LIGHT
   branch in `_wear_all`); ROM's `wear all` → `wear_obj` → WEAR_LIGHT would.
   Minor adjacent gap.
4. **ARITH triage remaining (7 ❌ MISSING)**: ARITH-004 (real level-0 weapon
   divergence — candidate fix), ARITH-017/018/019 (verify scroll/wand/potion/
   mobprog dispatch before any N/A reclass), ARITH-114 (per-race/class stat
   ceiling), ARITH-206/207 (`reset_handler` arg=0), ARITH-208 (UB-divisor).
5. **GitNexus read-only DB** — `gitnexus_impact`/`detect_changes` unavailable;
   reindex can't write. Fix DB perms/lock outside the session.
6. **Pre-existing lint** parked: B007/F841 cluster; F541 `shop.py:798`; I001
   `mud/world/movement.py:1-17`; F401/F841 in `test_equipment_system.py`.
7. **Pre-existing flake** `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
8. **Test side-effect** — some test mutates `data/areas/area.lst` (drops the
   `test.json` line); revert before committing. **Worktree hygiene** — locked
   worktrees still in `.claude/worktrees/`.
