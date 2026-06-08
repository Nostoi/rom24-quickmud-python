# Session Summary — 2026-06-08 — HANDLER affect_join implementation

## Scope

Picked up directly from the INV-040 handoff. The previous session had filed
`affect_join` miss as an open finding: ROM `src/update.c:839` calls
`affect_join(vch, &plague)` rather than `affect_to_char` directly, so a victim
who already carries plague receives a merged entry (averaged level, summed
duration/modifier), not two stacked entries. Python was calling `affect_to_char`
directly, stacking them.

## Outcomes

### `affect_join` — ✅ IMPLEMENTED

- **Python**: `mud/handler.py:affect_join` (new function, inserted between
  `affect_remove` and `affect_to_obj`)
- **ROM C**: `src/handler.c:1464-1483`
- **Fix**:
  - New module-level function `affect_join(ch, paf)` in `mud/handler.py`
    mirrors ROM exactly: iterate `ch.affected` for same `type`; when found,
    `paf.level = (paf.level + paf_old.level) // 2` (averages; levels are
    always positive so `//` == C integer division), `paf.duration +=
    paf_old.duration`, `paf.modifier += paf_old.modifier`,
    `affect_remove(ch, paf_old)`, `break`; then
    `ch.affect_to_char(paf)` unconditionally.
  - `mud/game_loop.py:_char_update_tick_effects` plague-spread path updated
    to call `affect_join(vch, new_af)` instead of `vch.affect_to_char(new_af)`.
    The old `hasattr(vch, "affect_to_char")` dispatch + fallback removed in
    favour of a direct `affect_join` call (which internally duck-types via
    `getattr`).
- **Tests added**: 4 new integration tests in
  `tests/integration/test_affect_join_merge.py`:
  - `test_affect_join_merges_existing_affect` — victim with existing plague
    receives one merged entry, not two
  - `test_affect_join_averages_level_and_sums_fields` — verifies level=(4+8)//2=6,
    duration=10+6=16, modifier=-3+(-5)=-8
  - `test_affect_join_no_existing_applies_fresh` — no existing affect → behaves
    like affect_to_char (single entry, bitvector + stat mod applied)
  - `test_affect_join_applies_merged_stat_modifier_once` — net STR change is
    baseline−8 (old −3 removed; merged −8 applied), not baseline−11 (double-apply)
- **Pre-existing tests**: 6 tests in `tests/test_handler_affects_rom_parity.py`
  (`TestAffectJoin`) were already written against the correct contracts but
  failing due to missing implementation — all 6 now pass.
- **Audit doc**: `docs/parity/HANDLER_C_AUDIT.md` `affect_join` row flipped
  ⚠️ Needs Audit → ✅ Implemented; affects-system note updated to 100% (11/11).

## Files Modified

- `mud/handler.py` — added `affect_join` function (26 lines)
- `mud/game_loop.py` — plague-spread path calls `affect_join` instead of `affect_to_char`
- `tests/integration/test_affect_join_merge.py` — new, 4 integration tests
- `docs/parity/HANDLER_C_AUDIT.md` — flipped `affect_join` row; updated 91% → 100%
- `CHANGELOG.md` — added [2.13.29] Fixed entry
- `pyproject.toml` — 2.13.28 → 2.13.29

## Test Status

- `pytest tests/integration/test_affect_join_merge.py -n0 -v` — 4/4 passing
- `pytest tests/test_handler_affects_rom_parity.py -k affect_join -n0 -v` — 6/6 passing
- Full suite: 5451 passing, 4 skipped

## Next Steps

One remaining secondary target from the INV-040 session:

1. **`shop_sell_keeper_broke` diff-harness scenario** — needs `__mob_gold=0` /
   `__mob_silver=0` meta-commands in `diffmain.c` + `pyreplay.py` to zero out
   keeper wealth so the "I'm broke" sell-path is exercised via the diff harness.

Cross-file invariants / diff-harness expansion remains the active mode
(per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
Next candidate areas: position-transition guards, `affect_strip` contract
(does it clear bitvectors?), or more diff-harness scenario coverage.
