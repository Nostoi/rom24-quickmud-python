# Session Status — 2026-06-08 — BUY-007/ACT-CAP: keeper message capitalisation + quote order (2.13.27)

## Current State

- **Active mode**: cross-file invariants / diff-harness expansion (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **BUY-007/ACT-CAP closed (2.13.27).** `_keeper_says` and `_act_to_char` now
    apply `capitalize_act_line` (mirroring ROM `src/comm.c:2376-2379`) and use
    ROM-exact suffix strings. 4 call sites updated with correct closing-quote
    placement. 5 wrong test assertions fixed.
  - **Diff-harness `shop_buy_insufficient_funds` added (2.13.27).** C golden
    captured; Python replay passes. Locks the keeper-voiced "can't afford" error
    exit end-to-end.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_BUY007_ACT_CAP_KEEPER_MESSAGE_FORMAT.md](SESSION_SUMMARY_2026-06-08_BUY007_ACT_CAP_KEEPER_MESSAGE_FORMAT.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.27 |
| Tests | 5445 passing, 4 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 10 static + 16 generated-oracle tests |
| Diff-harness shop scenarios | `shop_buy_weapon`, `shop_sell_weapon`, `shop_buy_insufficient_funds` |
| Shop integration tests | 15 passing |

## Next Intended Task

**Cross-INV affect-tick ordering** — probe `src/update.c:char_update` affect-expiry
loop vs `mud/world/update.py:char_update`. The loop traversal order (forward vs
backward, in-place mutation) is a candidate cross-file invariant. Method: read the
ROM C affect-expiry loop, read the Python equivalent, write one failing enforcement
test, then either close as a gap or file as the next free INV-NNN.

Secondary target: **`shop_sell_keeper_broke` diff-harness scenario** — needs
`__mob_gold=0`/`__mob_silver=0` meta-commands in `diffmain.c` + `pyreplay.py`.
