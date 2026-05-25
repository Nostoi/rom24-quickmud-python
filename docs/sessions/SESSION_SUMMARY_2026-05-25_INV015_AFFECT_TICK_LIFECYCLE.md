# Session Summary — 2026-05-25 — INV-015 AFFECT-TICK-LIFECYCLE (2.9.7)

## Scope

Single-cluster session under the "cross-file invariants is active" pass
(declared in commit `b3f53faf`). Picked up from `v2.9.6` with the
per-file audit tracker exhausted and the cross-file watch list empty.
The 5-minute probe targeted candidate area #1 from the session
prompt — **affect ticks** (`src/update.c:affect_update` →
`src/handler.c:affect_remove`) — and turned up a real divergence
within the probe itself. Filed as **INV-015 AFFECT-TICK-LIFECYCLE**
rather than a bare gap-closer because the contract spans
`mud/affects/engine.py`, `mud/handler.py`, and the apply-side dual
path in `mud/models/character.py`.

## Outcomes

### `INV-015` — ✅ ENFORCED

- **Python**: `mud/handler.py:affect_remove` (new), `mud/affects/engine.py:tick_spell_effects` (rerouted)
- **ROM C**: `src/update.c:762-786 affect_update`, `src/handler.c:1317-1359 affect_remove`, `src/handler.c:1182-1234 affect_check`
- **Contract**: every `AffectData` whose `duration` decrements to 0
  must (1) have its stat modifier subtracted via `affect_modify(FALSE)`,
  (2) have its bitvector cleared from `affected_by` / `imm_flags` /
  `res_flags` / `vuln_flags` and reconsidered against remaining
  affects via `affect_check`, (3) be unlinked from `ch.affected`.
- **Pre-fix divergence**: `mud/affects/engine.py:tick_spell_effects`
  was a bare `affected.remove(affect)` on expiry. For any
  `AffectData` whose `type` was the ROM-canonical integer spell SN,
  the `isinstance(spell_name, str)` guard at `engine.py:32` skipped
  the `spell_effects` cleanup branch, so the stat modifier and the
  bitvector both leaked permanently. Equipment-applied affects
  (`equip_char` calls `affect_modify(True)`) were the production
  surface — every tick that expired one of those entries left a
  permanent stat boost and a phantom `affected_by` bit.
- **Fix**: added module-level `mud/handler.py:affect_remove(ch, paf)`
  mirroring `src/handler.c:1317` exactly — `affect_modify(False)` →
  `affected.remove(paf)` → `affect_check(where, vector)`. Re-routed
  the expiry branch in `tick_spell_effects` through it.
- **Surfaced sub-divergence** (resolved in same commit): the naive
  re-route double-unwound for spells applied via the
  `Character.apply_spell_effect` path (frenzy, bless, weaken, etc.).
  Those entries are *shadow mirrors* in `ch.affected` — their
  modifier was never re-applied via `affect_modify(True)`, so
  calling `affect_modify(False)` on them subtracted a mod that
  wasn't there. Caught by 3 regressions:
  - `tests/integration/test_spell_affects_persistence.py::TestSpellAffectPersistence::test_spell_affect_expires_after_duration`
  - `tests/integration/test_spell_affects_persistence.py::TestSpellAffectStacking::test_multi_entry_spell_wears_off_once_through_game_tick`
  - `tests/test_affects.py::test_affect_to_char_applies_stat_modifiers`
  
  Resolution: explicit split at the tick call site. Spell-effects-
  managed entries (`isinstance(spell_name, str) and spell_name in effects`)
  keep bare list removal — `remove_spell_effect` already handles
  their stat unwind. Raw ROM-canonical entries route through
  `affect_remove`. The split is documented in both the engine.py
  call-site comment and the INV-015 tracker row.
- **Tests**: 2 new in `tests/integration/test_inv015_affect_tick_lifecycle.py`
  - `test_affect_with_stat_mod_undoes_on_tick_expiry` — pins the
    stat unwind + bitvector clear contract.
  - `test_affect_check_preserves_bit_if_another_affect_provides_it` —
    pins ROM `affect_check`: when two affects share a bitvector and
    only one expires, the bit must survive.
- **Suite**: 4714 passed, 4 skipped, 0 failed (was 4712 + 2 INV-015).

## Files Modified

- `mud/handler.py` — added `affect_remove` (module-level, 30 lines).
- `mud/affects/engine.py` — import `affect_remove`; expiry branch now
  splits ROM-canonical vs spell-effects-managed entries.
- `tests/integration/test_inv015_affect_tick_lifecycle.py` — new file,
  2 tests.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added INV-015 row,
  bumped budget note to "15 of ~20".
- `CHANGELOG.md` — added `## [2.9.7]` Fixed section.
- `pyproject.toml` — 2.9.6 → 2.9.7.

## Test Status

- `pytest tests/integration/test_inv015_affect_tick_lifecycle.py` — 2/2 passing.
- `pytest tests/integration/test_spell_affects_persistence.py` — 9/9 passing (split resolution verified).
- Full suite: 4714 passed, 4 skipped, 0 failed (`pytest -q`, 657s wall).

## Next Steps

1. **Sibling-leak sweep** (option #2 from the cluster-end menu): the
   pre-existing `Character.affect_remove` helper at
   `mud/models/character.py:862` clears the bitvector but never calls
   `affect_modify(False)`. Zero callers today, so the bug is dormant,
   but belt-and-suspenders if we anticipate wiring it in. One
   targeted gap-closer commit each for: route `Character.affect_remove`
   through the new module-level `affect_remove`; verify
   `remove_spell_effect`'s stat-unwind is the canonical path.
2. **Next cross-file invariant probe** (option #3): position
   transitions (POS_DEAD ↔ POS_INCAP ↔ POS_STUNNED ↔ POS_SLEEPING ↔
   POS_STANDING). Partial coverage via INV-002 (death/prompt) and
   INV-004 (PC death/connection); the full transition table per
   `src/fight.c:update_pos`, `src/act_info.c:do_wake/do_sleep`, and
   `src/handler.c:position_lookup` isn't pinned.
