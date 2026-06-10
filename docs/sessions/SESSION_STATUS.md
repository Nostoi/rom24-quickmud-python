# Session Status — 2026-06-10 — INV-041 Shopkeeper pShop Coherence (2.13.60)

## Current State

- **Active mode**: cross-file invariants pass — **INV-041 closed this session**
- **Last completed**:
  - **INV-041 SHOPKEEPER-PSOP-COHERENCE** — ROM `src/fight.c:1040 is_safe` checks
    `victim->pIndexData->pShop != NULL`. Python had two bugs: (1) `world_state.py`
    and `shop_loader.py` never wrote `MobIndex.pShop` from `shop_registry`; (2)
    `safety.py` checked `hasattr(victim, "pShop")` which always returns `False` on
    `MobInstance`. Fixed both loaders (write-back to `MobIndex.pShop`) and widened
    `is_safe` to walk the prototype chain. Enforcement test:
    `tests/integration/test_inv041_shopkeeper_psop_coherence.py` (3 tests).
  - **Class 7 signed-math divergence sweep (CLEAN)**: `compute_thac0`,
    `xp_compute`, dying penalty, AC clamping, alignment adjustments all correctly
    use `c_div` or have provably non-negative operands. No new gaps.
  - **Wizard-shop false alarm resolved**: `do_buy`/`do_sell` look up
    `shop_registry` directly (correctly populated from `data/shops.json`). The
    "latent parity gap" from the prior session was limited to the `is_safe` path.
  - Version 2.13.60.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_INV041_SHOPKEEPER_PSOP_COHERENCE.md](SESSION_SUMMARY_2026-06-10_INV041_SHOPKEEPER_PSOP_COHERENCE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.60 |
| Tests | 5498 passed, 5 skipped (full suite — 2.13.60) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 22 scenarios (Class 11 complete) |
| Class 11 dynamic widening | **COMPLETE** — all 15 mobprog dispatch paths have C-oracle ground truth |

## Next Intended Task

Cross-file invariants remains the active pass. Three candidates:

1. **Affect-tick edge contracts** — ROM `src/update.c:char_update` affect-expiry
   loop: `duration > 0` ticks unconditionally consume RNG; `duration == 0` fires
   wear-off and removes. Python's `mud/affects/engine.py:tick_spell_effects`
   implements this but the `msg_off` deduplication (only last affect of a type
   emits wear-off) is complex and warrants a targeted probe-then-scope pass. No
   INV row covers this surface yet.
2. **Position-transition invariants** — ROM position changes
   (STANDING→FIGHTING, DEAD→SLEEPING via `update_pos`) must trigger correct
   broadcasts and affect applications. No INV row covers this surface yet.
3. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
   for any unverified surface. Class 11 is complete; Classes 7 (signed math) and
   4 (async delivery) remain ongoing Layer B/C work.
