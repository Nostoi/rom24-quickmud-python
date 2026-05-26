# Session Summary — 2026-05-26 — INV-025 follow-up sweep (2.9.42)

## Scope

With INV-025 (`MOBPROG-ACT-TRIGGER-DISPATCH`) enforced at the emote
site in 2.9.40, this session wired `mp_act_trigger_room` into the
remaining ROM act() producers so TRIG_ACT mobprogs respond to the
full vocabulary of room events: give, drop, get, put, sacrifice,
equipment commands, and position transitions. One callsite (or
cohesive callsite cluster) per commit. The INV-025 contract itself
is unchanged — still locked at `do_emote`; the sweep widens coverage
without altering the enforced invariant.

GitNexus index refreshed at session start (was stale at `c75f898`,
now at `9cbbc6b6`). Note: refresh would need re-running again before
the next session as the seven sweep commits postdate the refresh.

## Outcomes

### `do_give` — ✅ SWEPT (2.9.40 sub-commit `e86d55aa`)

- **Python**: `mud/commands/give.py:do_give`
- **ROM C**: `src/act_obj.c:832-836` — `MOBtrigger = FALSE; act(...); MOBtrigger = TRUE;`
- **Fix**: Wrapped broadcast in `disable_mobtrigger()` and dispatched
  `mp_act_trigger_room`. The dispatch is wired (so the contract holds
  if a future caller drops the wrapper), but the wrapper suppresses
  TRIG_ACT per ROM. The explicit `mp_give_trigger` covers the give
  event.
- **Tests**: `tests/integration/test_inv025_do_give_act_trigger_suppression.py` — 1/1.

### `do_drop` — ✅ SWEPT (`68bff425`)

- **Python**: `mud/commands/inventory.py:do_drop`
- **ROM C**: `src/act_obj.c:586, 608, 632` — no MOBtrigger wrap.
- **Fix**: `mp_act_trigger_room` at all three drop sites (coins,
  single-obj, drop-all) plus the `MELT_DROP` "dissolves into smoke"
  follow-up.
- **Tests**: `test_inv025_do_drop_act_trigger_dispatch.py` — 1/1.

### `do_get` — ✅ SWEPT (`47109d66`)

- **Python**: `mud/commands/inventory.py:do_get`
- **ROM C**: `src/act_obj.c:151, 158` — no MOBtrigger wrap.
- **Fix**: `mp_act_trigger_room` on get-from-container and
  get-from-floor.
- **Tests**: `test_inv025_do_get_act_trigger_dispatch.py` — 1/1.

### `do_put` — ✅ SWEPT (`869ccda1`)

- **Python**: `mud/commands/obj_manipulation.py:do_put`
- **ROM C**: `src/act_obj.c:440-446, 479-485` — no MOBtrigger wrap.
- **Fix**: `mp_act_trigger_room` at all four broadcast sites
  (single/all × on/in). Also fixed a latent bug — `do_put` was
  reading `char.location` (an `Affect` attribute, not a `Character`
  attribute) instead of `char.room`, so the broadcast never reached
  room observers; switched to `char.room` consistent with ROM's
  `ch->in_room`.
- **Tests**: `test_inv025_do_put_act_trigger_dispatch.py` — 1/1.

### `do_sacrifice` — ✅ SWEPT (`222c857f`)

- **Python**: `mud/commands/obj_manipulation.py:do_sacrifice`
- **ROM C**: `src/act_obj.c:1856` — no MOBtrigger wrap.
- **Fix**: `mp_act_trigger_room` on the "$n sacrifices $p to Mota."
  broadcast.
- **Tests**: `test_inv025_do_sacrifice_act_trigger_dispatch.py` — 1/1.

### Equipment commands — ✅ SWEPT (`672a59c6`)

- **Python**: `mud/commands/equipment.py`, `mud/commands/obj_manipulation.py`
- **ROM C**: `src/act_obj.c:1419, 1435-1612, 1639, 1674`,
  `src/handler.c:remove_obj` — no MOBtrigger wraps.
- **Fix**: `mp_act_trigger_room` at every equipment broadcast site —
  `do_wear` (standard wear), `do_wield`, `do_hold`/light, `_wear_all`,
  the shared `_unequip_to_inventory` "stops using" path in
  `equipment.py`, and the canonical `_perform_remove` path in
  `obj_manipulation.py`.
- **Tests**: `test_inv025_equipment_act_trigger_dispatch.py` — 2/2
  (wear, remove).

### Position-transition broadcasts — ✅ SWEPT (`9cbbc6b6`)

- **Python**: `mud/combat/engine.py:_broadcast_pos_change`
- **ROM C**: `src/fight.c:837-861` — MORTAL, INCAP, STUNNED, DEAD —
  no MOBtrigger wraps.
- **Fix**: `mp_act_trigger_room` at the end of the central
  `_broadcast_pos_change` helper, used by `apply_position_change`,
  `holy_word`, `decay_corpse`, and every spell that calls
  `update_pos` directly.
- **Tests**: `test_inv025_position_transition_act_trigger_dispatch.py` — 1/1.

## Files Modified

- `mud/commands/give.py` — disable_mobtrigger() wrap + dispatch
- `mud/commands/inventory.py` — do_drop + do_get dispatch
- `mud/commands/obj_manipulation.py` — do_put (incl. `char.location` →
  `char.room` fix) + do_sacrifice + `_perform_remove` dispatch
- `mud/commands/equipment.py` — wear / wield / hold / wear-all /
  unequip dispatch
- `mud/combat/engine.py` — `_broadcast_pos_change` dispatch
- 7 new test files under `tests/integration/test_inv025_*` (8 tests)
- `CHANGELOG.md` — 2.9.42 section
- `pyproject.toml` — 2.9.41 → 2.9.42
- `docs/sessions/SESSION_STATUS.md` — overwritten to 2.9.42 snapshot

## Test Status

- All 8 new INV-025 sweep tests pass.
- Integration suite carried forward unchanged from 2.9.41 (full
  suite run kicked off at session end; spot-checks against `give`,
  `drop`, `get`, `put`, `container`, `wear`, `wield`, `remove`,
  `equipment`, `hold`, `fight`, `combat`, `position`, `inv025`,
  `pos_change` filters all green).
- Latent `test_mpedit_001_interpret_mpedit::test_mpedit_show_on_empty_input`
  test-ordering flake reproduced both with and without these changes
  — pre-existing.

## Next Steps

1. **Continue probe-then-scope at 22/~20 INV budget**. The sweep
   landed seven INV-025 follow-up commits without filing any new INV
   rows — coverage widened, contract count unchanged. Methodology is
   working.
2. **Latent `char.location` audit** — `do_put` surfaced a real bug
   reading `char.location` instead of `char.room`. Worth grepping
   for other `getattr(char, "location"` callsites to see whether
   the typo cluster goes further. Initial scan during this session
   surfaced one in `do_quaff` (uses `char.room or char.location`
   fallback — harmless because `char.room` wins) and the now-fixed
   `do_remove` fallback. No urgency; file as next-session probe if
   nothing higher priority surfaces.
3. **GitNexus refresh** — index is stale at `c75f898`; refresh
   before the next probe session so `gitnexus_impact` calls return
   accurate blast-radius numbers for the seven sweep commits.
