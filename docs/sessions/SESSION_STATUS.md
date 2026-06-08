# Session Status — 2026-06-08 — Diff-Harness shop sell + do_sell/do_buy parity (2.13.21)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness shop sell (2.13.21).** Four parity bugs fixed in `do_sell`/`do_buy`:
    1. Player credit was a total-rebalance; fixed to incremental `gold += price//100; silver += price%100`
       (FINDING-028, mirroring ROM `src/act_obj.c:2938-2939`).
    2. `number_percent()` RNG call was gated on `haggle_skill > 0`; ROM always draws
       unconditionally (`src/act_obj.c:2925`) — same class as FIGHT-021/022.
    3. Keeper deduction was `_set_keeper_total_wealth(total - price)` (rebalance); fixed to
       `deduct_cost(keeper, price)` (FINDING-029, mirroring ROM `src/act_obj.c:2940`).
    4. Keeper credit in `do_buy` was also a rebalance; fixed to incremental `gold += cost//100;
       silver += cost%100` (FINDING-029, mirroring ROM `src/act_obj.c:2747-2748`).
  - `normalize_step` in `compare.py` now sorts `chars` by key and `rooms` by vnum so the
    list equality check agrees with the dict-keyed per-field renderer (fixes "no field
    localized" false failures when multiple watch-chars emit in different insertion orders).
  - `test_generated_shop_sell_matches_live_c` added; `load_weaponsmith` +
    `sell_sword_to_weaponsmith` Hypothesis rules; weaponsmith added to `teardown()` watch_chars.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_DIFF_HARNESS_SHOP_SELL.md](SESSION_SUMMARY_2026-06-08_DIFF_HARNESS_SHOP_SELL.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.21 |
| Tests | 5434+ passed, 0 failed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 8 static + 15 generated-oracle tests |
| Diff-harness position rules | sit/rest/sleep/stand/wake — full ROM graph |
| Diff-harness affect rules | learn_and_cast_armor + char_update_tick (up to 8/run) |
| Diff-harness shop rules | load_weaponsmith + sell_sword_to_weaponsmith |

## Next Intended Task

1. **`do_buy` diff-harness scenario** — the buy-side of the transaction is not yet oracle-verified.
   Add a `__mob_carry=<vnum>` meta-command (C shim + Python replay) so the keeper can be given
   specific stock before the test character buys it. Add `buy_sword_from_keeper` Hypothesis rule
   and `test_generated_shop_buy_matches_live_c` static scenario. The incremental keeper-credit
   fix (just landed) will be verified here.
2. **Mob scripts** (`mob_prog.c`) — `mprog_act_trigger`/`mprog_entry_trigger` entry-level probes;
   no RNG alignment needed for basic trigger tests.
3. **Additional spells** — `detect_evil`, `fly`, `bless`; seed alignment for the skill check.
4. Cross-INV candidates: affect-tick ordering contracts (call order in `char_update` vs ROM),
   shop transaction atomicity (gold deducted before item transfer in both engines?).
