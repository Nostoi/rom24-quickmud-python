# Session Summary — 2026-06-08 — INV-040: affect_to_char must call affect_modify(TRUE)

## Scope

Picked up from the 2.13.27 BUY-007/ACT-CAP handoff. Active mode is cross-file
invariants / diff-harness expansion (per-file audit tracker has no ⚠️ Partial /
❌ Not Audited rows). The intended task from SESSION_STATUS.md was to probe
`src/update.c:char_update`'s affect-expiry loop traversal order as a cross-INV
candidate.

The probe found two tightly coupled bugs in the `Character.affect_to_char` path:
(1) the method did not call `affect_modify(True)`, silently dropping stat
modifiers; (2) `mud/game_loop.py` passed `location="str"` (a string) instead of
`location=1` (APPLY_STR integer), so even if `affect_modify` had been called it
would fall through all integer-comparison branches and still drop the modifier.
Both bugs conspire so plague-spread victims never receive the -5 STR penalty
(ROM `src/update.c:825 plague.location = APPLY_STR` + `src/handler.c:1278
affect_to_char → affect_modify(ch, paf_new, TRUE)`).

## Outcomes

### INV-040 AFFECT-TO-CHAR-FULL-APPLY — ✅ ENFORCED

- **Python (fix 1)**: `mud/models/character.py:Character.affect_to_char`
  - Added lazy import of `affect_modify` from `mud.handler`
  - Now calls `affect_modify(self, affect, True)` before `self.affected.append`
  - Removed the old manual `self.affected_by |= affect.bitvector` (affect_modify
    handles all bitvector types including TO_IMMUNE/TO_RESIST/TO_VULN)
- **Python (fix 2)**: `mud/game_loop.py:_char_update_tick_effects` plague-spread
  - `location="str"` → `location=1` with comment `# APPLY_STR — ROM src/update.c:825`
- **ROM C**: `src/handler.c:1266-1280` (affect_to_char) + `src/update.c:825`
- **Fix**: `affect_to_char` now fully mirrors ROM: apply stat mods and bitvectors
  via `affect_modify`, then insert into affected list.
- **Tests added**: 2 new tests in `tests/integration/test_inv040_affect_to_char_full_apply.py`
  - `test_plague_spread_applies_str_modifier` — integration test through full plague
    tick with monkeypatched RNG/saves; asserts victim gets AFF_PLAGUE AND STR -5
  - `test_affect_to_char_applies_stat_modifier_directly` — unit test: calling
    `affect_to_char` with APPLY_STR/-3 modifier must reduce `mod_stat[STR]` by 3

### Open separate finding: `affect_join` miss in plague-spread

ROM `src/update.c:839` calls `affect_join(vch, &plague)` — not `affect_to_char`
directly. `affect_join` (handler.c:1464-1483) searches for an existing same-type
affect on the victim, merges level/duration/modifier, then calls `affect_to_char`.
Python calls `affect_to_char` directly, so re-infection stacks a second plague
entry instead of merging. This is a separate bug, filed as ⚠️ Partial `affect_join`
in `docs/parity/HANDLER_C_AUDIT.md`. Not fixed this session.

## Files Modified

- `mud/models/character.py` — `Character.affect_to_char` now calls `affect_modify(True)`
- `mud/game_loop.py` — plague-spread AffectData `location="str"` → `location=1`
- `tests/integration/test_inv040_affect_to_char_full_apply.py` — new, 2 tests
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added INV-040 row; budget note updated to 25
- `CHANGELOG.md` — added [2.13.28] Fixed entry
- `pyproject.toml` — 2.13.27 → 2.13.28

## Test Status

- `pytest tests/integration/test_inv040_affect_to_char_full_apply.py -v -n0` — 2/2 passing
- Full suite: 5447 passing, 4 skipped (1 pre-existing parallel-flake, passes in isolation)

## Next Steps

Two remaining candidates from the original session probe:

1. **`affect_join` for plague re-infection** (separate finding filed above):
   implement `affect_join` in `mud/handler.py` and update `mud/game_loop.py:_char_update_tick_effects`
   to call it instead of `affect_to_char` directly. ROM ref: `src/handler.c:1464-1483`.

2. **`shop_sell_keeper_broke` diff-harness scenario** (secondary from previous session):
   needs `__mob_gold=0`/`__mob_silver=0` meta-commands in `diffmain.c` + `pyreplay.py`
   to let the scenario zero out keeper wealth so "I'm broke" path is exercised.
