# Session Status — 2026-06-08 — HANDLER affect_join implementation (2.13.29)

## Current State

- **Active mode**: cross-file invariants / diff-harness expansion (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **HANDLER `affect_join` FIXED (2.13.29).** `affect_join` added to
    `mud/handler.py` mirroring ROM `src/handler.c:1464-1483`. Plague re-infection
    path in `mud/game_loop.py` updated to call `affect_join` (merge semantics)
    instead of `affect_to_char` directly (stack semantics).
    10 tests covering `affect_join` now pass (4 new + 6 pre-existing).
    `HANDLER_C_AUDIT.md` affects system: 100% complete (11/11 functions).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_HANDLER_AFFECT_JOIN.md](SESSION_SUMMARY_2026-06-08_HANDLER_AFFECT_JOIN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.29 |
| Tests | 5451 passing, 4 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 16 generated-oracle tests |
| Diff-harness shop scenarios | `shop_buy_weapon`, `shop_sell_weapon`, `shop_buy_insufficient_funds` |
| Shop integration tests | 15 passing |

## Next Intended Task

**`shop_sell_keeper_broke` diff-harness scenario** — add `__mob_gold=0` /
`__mob_silver=0` meta-commands to `tools/diff_harness/diffmain.c` and
`tools/diff_harness/pyreplay.py` so the harness can zero out a shopkeeper's
treasury. Then author `tools/diff_harness/scenarios/shop_sell_keeper_broke.json`
and capture the golden. This exercises the "keeper can't afford it" sell-error path
end-to-end in both the C and Python engines.

Secondary: **cross-file invariant candidates** — position-transition guards
(does `do_sit`/`do_rest`/`do_stand` correctly gate on current position?),
`affect_strip` bitvector-clear contract, or additional diff-harness scenario
coverage for areas not yet exercised (e.g. combat sub-paths, group commands).
