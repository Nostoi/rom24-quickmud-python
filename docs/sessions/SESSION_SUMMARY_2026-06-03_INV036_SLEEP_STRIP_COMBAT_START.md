# Session Summary — 2026-06-03 — INV-036 sleep affect strip on combat start

## Scope

Continued from `SESSION_STATUS.md` after INV-035. Active mode remains
cross-file invariants via probe-then-scope. Chosen probe: position-transition
edges around ROM `src/fight.c:set_fighting`.

## Probe Result

ROM `set_fighting` (`src/fight.c:1416-1433`) strips magical sleep before setting
`ch->fighting` and `POS_FIGHTING`:

- `IS_AFFECTED(ch, AFF_SLEEP)` gates `affect_strip(ch, gsn_sleep)`.
- `affect_strip` (`src/handler.c:1426-1438`) walks `ch->affected` and calls
  `affect_remove` for each matching `AFFECT_DATA`.
- Therefore combat start must unlink raw sleep affect data, not only clear the
  `AFF_SLEEP` bit or remove a high-level spell-effect mirror.

Python `Character.strip_affect("sleep")` already removed `SpellEffect` sleep and
cleared bare `AFF_SLEEP`, but a raw `AffectData(type="sleep", bitvector=AFF_SLEEP)`
remained in `character.affected`.

## Outcome — INV-036 (✅ ENFORCED, 2.12.84)

Filed `INV-036 SLEEP-AFFECT-STRIP-ON-COMBAT-START` in
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

Added `tests/integration/test_inv036_sleep_strip_on_combat_start.py`, which
failed before the fix because the raw sleep `AffectData` stayed linked after
`set_fighting`.

Fixed `mud/models/character.py:Character.strip_affect` so raw sleep affects
route through `mud.handler.affect_remove`, preserving ROM's
`affect_modify(FALSE)` + `affect_check` behavior. The existing `SpellEffect`
path and the legacy bit-only fallback remain intact.

## Files Modified

- `mud/models/character.py` — raw sleep `AffectData` removal in `strip_affect`.
- `tests/integration/test_inv036_sleep_strip_on_combat_start.py` — new RED/GREEN
  regression guard.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — new INV-036 row.
- `CHANGELOG.md` — Added entry for INV-036.
- `pyproject.toml` — version `2.12.83` → `2.12.84`.
- `docs/sessions/SESSION_STATUS.md` — refreshed canonical pointer.

## Verification

- `pytest -n0 tests/integration/test_inv036_sleep_strip_on_combat_start.py -q`
  — failed RED before fix, passed after fix.
- `pytest -n0 tests/integration/test_inv036_sleep_strip_on_combat_start.py tests/test_combat_state.py tests/integration/test_inv015_affect_tick_lifecycle.py tests/integration/test_restore_strips_affects.py -q`
  — 7 passed.
- `pytest -n0 tests/test_fighting_state.py tests/test_combat_state.py -q` —
  19 passed.
- `ruff check mud/models/character.py tests/integration/test_inv036_sleep_strip_on_combat_start.py`
  — clean.
- `gitnexus_impact(strip_affect)` — CRITICAL pre-change blast radius (direct
  callers: `set_fighting`, `check_killer`, `_restore_char`), reported before
  edit.
- `gitnexus_detect_changes(scope="all")` — LOW risk, 0 affected processes.

## Next Steps

Candidate next passes:

1. `diff_harness` Hypothesis widening (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — highest-ceiling, multi-day.
2. New cross-INV probe area: affect ticks, group/follower chain, or another
   position-transition edge.
3. INV tracker consolidation: active enforced count remains above the soft
   ~20-row budget.
