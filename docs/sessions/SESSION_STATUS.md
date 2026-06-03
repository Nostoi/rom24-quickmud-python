# Session Status — 2026-06-03 — FINDING-026 diff light/shop widening (2.13.9)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **FINDING-026 — shop sell/value duplicate-stock pricing + wording** ✅
    RESOLVED (2.13.9). The new `shop_sell_weapon` differential scenario found
    Python quoting an oloaded wooden staff at 174 coins while ROM quoted 116
    coins, plus ROM `act()` capitalization/punctuation differences. `_get_cost`
    now reads `ITEM_INVENTORY` from the keeper's carried object flags, `do_value`
    uses ROM act-style capitalization/punctuation, and `do_sell` emits ROM's
    silver+gold wording.
  - **Diff-harness Phase C widening**: added `light_hold` and
    `shop_sell_weapon` deterministic scenarios with committed C goldens, plus
    `__hour=<n>` meta-command support on both C and Python replay sides.
  - **FINDING-025 — mob equip/disarm** ✅ RESOLVED (2.13.8).
    `MobInstance.equip`'s inventory+`wear_loc` model was verified as
    ROM-faithful; the real gap was shared consumers. `get_wielded_weapon` now
    scans carried objects by `wear_loc`, `MobInstance.remove_object` clears
    carrier/`wear_loc`, and `disarm` mirrors ROM's NODROP/INVENTORY carry-list
    branch plus the NPC immediate visible-weapon reclaim branch.
  - **FINDING-024 — save/load carry-list ordering** ✅ RESOLVED (2.13.7).
    `ObjectSave` persists `Object._carry_seq`, `_deserialize_object` restores it,
    and `from_orm` advances the runtime carry-sequence counter past restored
    values.
  - **FINDING-020 — equip→remove carry-list position** ✅ RESOLVED (PC path,
    2.13.6).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_FINDING_026_DIFF_LIGHT_SHOP.md](SESSION_SUMMARY_2026-06-03_FINDING_026_DIFF_LIGHT_SHOP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.9 |
| Tests | Diff-harness slice `python3 -m pytest -n0 tests/test_differential_smoke.py tests/test_diff_harness_unit.py -q` → **19 passed**; shop slice `python3 -m pytest -n0 tests/test_shops.py -q` → **35 passed**; `python3 -m tools.diff_harness.capture --check` → all 6 scenarios ok; `ruff check .` clean; `ruff format --check mud/commands/shop.py tools/diff_harness/pyreplay.py tests/test_shops.py` clean |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Divergence class 13 | object-list ordering + equipment representation legs closed (INV-039 + FINDING-020 + FINDING-024 + FINDING-025); deterministic shop/light diff scenarios added |
| Open engine findings | None currently called out in the latest session pointer |

## Next Intended Task

1. Continue Phase C deterministic diff-harness widening on adjacent no-RNG money
   paths (`drop <amount> gold/silver`, `get coins`, `give coins`).
2. Add RNG-locked combat scenarios only after seed alignment is proven.

## Other open / deferred items

- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.
