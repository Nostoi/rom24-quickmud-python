# Session Status — 2026-06-08 — BUY-006/SELL-002/SELL-003: shop error-exit parity (2.13.26)

## Current State

- **Active mode**: cross-file invariants / diff-harness expansion (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **BUY-006/SELL-002/SELL-003 closed (2.13.26).** Three shop error-exit divergences
    fixed: `do_buy` afford-before-level reorder (ROM `src/act_obj.c:2688` vs `2702`);
    `do_sell` can't-see and not-interested messages updated to use `_act_to_char`
    `$n`/`$p` expansion instead of hardcoded "The shopkeeper…" strings. 3 integration
    tests added.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_BUY006_SELL002_SELL003_SHOP_ERROR_PATHS.md](SESSION_SUMMARY_2026-06-08_BUY006_SELL002_SELL003_SHOP_ERROR_PATHS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.26 |
| Tests | 5444+ passing (suite not re-run in full this session) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 9 static + 16 generated-oracle tests |
| Diff-harness shop rules | load_weaponsmith + sell_sword + stock_keeper_sword + buy_sword |
| Shop integration tests | 15 passing (error-paths + broadcasts + haggle + pet + OLC) |

## Next Intended Task

**Diff-harness error-path scenarios** — now that BUY-006/SELL-002/SELL-003 are
fixed, the message output is ROM-correct. Author:

1. `shop_buy_insufficient_funds` scenario — `__silver=0 __gold=0`, weaponsmith
   loaded (`__mload=3003`), stocked with long sword (`__mob_carry=3022`), then
   `buy sword`. Watch: Tester messages. Expected: "can't afford to buy a long sword".
   No new meta-commands needed.

2. (Optional) `shop_sell_keeper_broke` scenario — needs `__mob_gold=0`/`__mob_silver=0`
   meta-commands in `diffmain.c` + `pyreplay.py` to zero keeper wealth after
   `__mload`, since weaponsmith `wealth=25000` → ~125-375 gold from RNG.

3. **Cross-INV affect-tick ordering** — `char_update` affect traversal order vs
   ROM C `src/update.c:char_update` — the longer-term next invariant target.
