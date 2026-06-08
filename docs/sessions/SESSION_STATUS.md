# Session Status — 2026-06-08 — Diff-Harness shop buy + __mob_carry meta-command (2.13.22)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness shop buy (2.13.22).** `__mob_carry=<vnum>` meta-command added to both
    the C shim (`diffmain.c`) and Python replay (`pyreplay.py`): spawns an object and adds
    it to the first NPC's carry list (`obj_to_char` only, no `equip_char`). Static scenario
    `shop_buy_weapon` (room 3001, weaponsmith 3003, small sword 3021, buy price 300 silver),
    golden captured from C oracle, `test_generated_shop_buy_matches_live_c` static test, and
    two new Hypothesis rules (`stock_keeper_sword` / `buy_sword_from_keeper`) in
    `DeterministicNoRngDiffMachine`. Oracle confirms: player silver 300→0, gains sword;
    keeper gold 246→249 (incremental +3 — 2.13.21 keeper credit fix verified by C).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_DIFF_HARNESS_SHOP_BUY.md](SESSION_SUMMARY_2026-06-08_DIFF_HARNESS_SHOP_BUY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.22 |
| Tests | 5433 passed, 0 failed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 8 static + 16 generated-oracle tests |
| Diff-harness position rules | sit/rest/sleep/stand/wake — full ROM graph |
| Diff-harness affect rules | learn_and_cast_armor + char_update_tick (up to 8/run) |
| Diff-harness shop rules | load_weaponsmith + sell_sword + stock_keeper_sword + buy_sword |

## Next Intended Task

1. **Mob scripts** (`mob_prog.c`) — `mprog_act_trigger`/`mprog_entry_trigger` entry-level
   probes. No RNG alignment needed for basic trigger tests. Add a diff-harness scenario with
   a mob that has a greeting/entry trigger and verify it fires identically in C and Python.
2. **Additional spells** — `detect_evil`, `fly`, `bless`; extend the `learn_and_cast_armor`
   Hypothesis pattern to these spells with appropriate seed alignment.
3. **Shop transaction atomicity** (INV candidate) — verify gold deducted from player before
   item transfer in both engines; probe error-exit paths (insufficient funds, item not for
   sale) for atomicity divergences.
4. Cross-INV candidates: affect-tick ordering contracts (call order in `char_update` vs ROM).
