# Session Status — 2026-06-08 — Diff-harness __mob_gold/__mob_silver meta-commands (2.13.32)

## Current State

- **Active mode**: cross-file invariants / diff-harness expansion (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **`__mob_gold=N` / `__mob_silver=N` meta-commands + `shop_sell_keeper_broke`
    scenario (2.13.32).** Two new diff-harness meta-commands (`src/diff_shim/diffmain.c`
    + `tools/diff_harness/pyreplay.py`) that zero out a shopkeeper's treasury. Used
    in the new `shop_sell_keeper_broke` scenario + live C-oracle differential test
    covering the ROM `do_sell` wealth-check early exit
    (`src/act_obj.c:2916-2921` — `"I'm afraid I don't have enough wealth to buy $p."`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_HARNESS_MOB_GOLD_SILVER_META_CMDS.md](SESSION_SUMMARY_2026-06-08_HARNESS_MOB_GOLD_SILVER_META_CMDS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.32 |
| Tests | 5452 passing, 5 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 17 generated-oracle tests |
| Diff-harness shop scenarios | `shop_buy_weapon`, `shop_sell_weapon`, `shop_buy_insufficient_funds`, `shop_sell_keeper_broke` |
| Shop integration tests | 15 passing |

## Next Intended Task

**Cross-file invariant candidates** — any of the following:

1. **Position-transition guards** (`do_sit`/`do_rest`/`do_stand` in `src/act_move.c`):
   probe whether Python `mud/commands/movement.py` correctly gates each transition on
   current position; write a failing test for the first missed guard; file as next free
   INV-NNN if root cause spans modules.
2. **`affect_strip` bitvector-clear contract**: verify Python `affect_strip` correctly
   clears the bitvector flag when removing the last affect of a given type.
3. **Hypothesis state machine extension**: add `sell_sword_to_broke_keeper` rule to
   `DeterministicNoRngDiffMachine` in `tools/diff_harness/generated.py` to fuzz
   the keeper-broke sell-error path alongside the existing sell/buy rules.
