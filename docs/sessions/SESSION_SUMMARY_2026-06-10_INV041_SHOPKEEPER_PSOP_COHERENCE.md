# Session Summary — 2026-06-10 — INV-041 Shopkeeper pShop Coherence

## Scope

Continuing from v2.13.59 (Class 11 complete). The "Next Steps" from the
TRIG_RANDOM/TRIG_DELAY session listed a "latent parity gap: wizard shop status"
— specifically that `_has_shop` returns False for production shopkeepers. This
session investigated that claim, found a broader gap in `is_safe` shopkeeper
detection, and ran the Class 7 (signed integer math) divergence-sweep to check
for `c_div`/`c_mod` misuse.

## Investigation summary (non-code findings)

- **Wizard shop false alarm resolved**: `do_buy`/`do_sell` work correctly — they
  look up `shop_registry` directly, which is correctly populated from
  `data/shops.json` at boot by `world_state.py`. Mob 3000 (wizard) is in
  `data/shops.json`; buy/sell parity is intact.
- **Real gap found in `is_safe`**: ROM `src/fight.c:1040` checks
  `victim->pIndexData->pShop != NULL` to block attacks on shopkeepers.
  Two independent bugs conspired to make every production shopkeeper attackable in
  Python:
  1. `world_state.py` and `shop_loader.py` each populate `shop_registry` but
     never write back `MobIndex.pShop` on the prototype in `mob_registry`. All
     production `MobIndex` objects had `pShop = None`.
  2. `safety.py:is_safe` checked `hasattr(victim, "pShop")` which always returns
     `False` for a `MobInstance` (the field lives on the prototype, not the
     instance).
- **Class 7 signed-math sweep (CLEAN)**: all high-risk signed-math division sites
  (`compute_thac0`, `interpolate`, `saves_spell`, `xp_compute`, dying penalty,
  alignment adjustments, AC clamping) correctly use `c_div` or have provably
  non-negative operands. No new gaps found.

## Outcomes

### INV-041 — SHOPKEEPER-PSOP-COHERENCE — ✅ ENFORCED

- **ROM C**: `src/fight.c:1040` — `if (victim->pIndexData->pShop != NULL)` blocks
  all attack attempts on shopkeepers
- **Python enforcement point**: `mud/combat/safety.py:is_safe` must check
  `victim.prototype.pShop`; all loaders must write `MobIndex.pShop` at boot
- **Root cause**: `world_state.py` called `shop_registry[keeper] = Shop(...)` but
  never `mob_registry[keeper].pShop = shop`. `shop_loader.py` had the same miss.
  `is_safe` used `hasattr(victim, "pShop")` — always `False` on `MobInstance`.

#### Fixes applied

**`mud/world/world_state.py`** (data/shops.json loader path):
```python
shop_registry[keeper] = shop
# NEW: mirror ROM src/db.c load_shops — write pShop onto MobIndex prototype
mob_proto = mob_registry.get(keeper)
if mob_proto is not None:
    mob_proto.pShop = shop
```

**`mud/loaders/shop_loader.py`** (`.are` file loader path):
```python
shop_registry[keeper] = shop
# NEW: same write-back for the .are file loader
mob_proto = mob_registry.get(keeper)
if mob_proto is not None:
    mob_proto.pShop = shop
```

**`mud/combat/safety.py`** — widened pShop check:
```python
# OLD: hasattr(victim, "pShop") and getattr(victim, "pShop", None)
# NEW: check instance + prototype chain (mirrors ROM pIndexData->pShop)
if getattr(victim, "pShop", None) is not None:
    return True
proto = getattr(victim, "prototype", None) or getattr(victim, "pIndexData", None)
if proto is not None and getattr(proto, "pShop", None) is not None:
    return True
```

- **Tests**: `tests/integration/test_inv041_shopkeeper_psop_coherence.py` — 3/3
  passing. Three cases: shopkeeper-is-safe (primary), non-shopkeeper-is-not-safe,
  and prototype-pShop-set-by-loader.

## Files Modified

- `mud/combat/safety.py` — widened `is_safe` pShop check to prototype chain
- `mud/world/world_state.py` — write `MobIndex.pShop` after `shop_registry` insert
- `mud/loaders/shop_loader.py` — same write-back for `.are` file loader path
- `tests/integration/test_inv041_shopkeeper_psop_coherence.py` — new enforcement
  test (3 tests)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-041 row added; budget
  count updated 25→26
- `docs/parity/FIGHT_C_AUDIT.md` — `is_safe` row annotated with INV-041 sub-bug
  and fix reference
- `CHANGELOG.md` — added [2.13.60] Fixed entry
- `pyproject.toml` — 2.13.59 → 2.13.60

## Test Status

- `pytest tests/integration/test_inv041_shopkeeper_psop_coherence.py` — 3/3 passed
- Full suite: **5498 passed, 5 skipped** (93.45s)

## Next Steps

Cross-file invariants remains the active pass. Candidates for the next session:

1. **Affect-tick edge contracts** — ROM `src/update.c char_update` affect-expiry
   loop: `duration > 0` ticks unconditionally consume RNG; `duration == 0` fires
   wear-off and removes. Python's `mud/affects/engine.py:tick_spell_effects`
   implements this but the `msg_off` deduplication (only last affect of a type
   emits wear-off) is complex and warrants a targeted probe-then-scope pass.
2. **Position-transition invariants** — ROM position changes (STANDING→FIGHTING,
   DEAD→SLEEPING via `update_pos`) must trigger correct broadcasts and affect
   applications (e.g. sanctuary drops at certain positions). No INV yet covers
   this surface.
3. **Divergence Class 7 (signed math)** — ongoing Layer B sweep; the combat
   `interpolate` call site in `mud/combat/engine.py` using `c_div` for `saving_throw`
   was confirmed correct this session. No new gaps.
