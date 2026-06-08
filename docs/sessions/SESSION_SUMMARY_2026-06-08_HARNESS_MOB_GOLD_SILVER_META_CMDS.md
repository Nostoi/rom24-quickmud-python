# Session Summary — 2026-06-08 — Diff-harness __mob_gold/__mob_silver meta-commands

## Scope

Short focused session. Picked up from the `SESSION_STATUS.md` "Next Intended Task"
which called for a `shop_sell_keeper_broke` diff-harness scenario to exercise the
ROM `do_sell` wealth-check early exit (`src/act_obj.c:2916-2921`). Prerequisite was
implementing two new meta-commands — `__mob_gold=N` and `__mob_silver=N` — that zero
out a shopkeeper's treasury so the guard fires regardless of the wealth rolled during
`__mload`.

## Outcomes

### `__mob_gold=N` / `__mob_silver=N` meta-commands — ✅ IMPLEMENTED

- **C shim**: `src/diff_shim/diffmain.c` — two new `strncmp` handlers after the
  existing `__silver=` block; walk `ch->in_room->people` for the first `IS_NPC(mob)`
  and set `mob->gold` / `mob->silver`.
- **Python replay**: `tools/diff_harness/pyreplay.py` — matching handlers using
  `next((p for p in char.room.people if isinstance(p, MobInstance)), None)`.
- **Design note**: `__mob_gold=0` / `__mob_silver=0` are placed *after* `__mload` in
  the scenario so the mob's ROM wealth rolls (`db.c:2047-2060`) run on both sides
  first, then are overwritten to zero. Zeroing before `__mload` would race the
  constructor's RNG calls.

### `shop_sell_keeper_broke` scenario + test — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/shop_sell_keeper_broke.json` — loads
  weaponsmith (vnum 3003) into room 3001, zeroes its treasury via `__mob_gold=0` /
  `__mob_silver=0`, then `sell sword` (vnum 3021, cost 250 silver).
- **ROM C path exercised**: `src/act_obj.c:2916-2921` — keeper voice
  `"I'm afraid I don't have enough wealth to buy $p."`. This path fires before the
  haggle `number_percent()` call (`src/act_obj.c:2925`), so no `__seed` bracket is
  needed around `sell sword`.
- **Test**: `tests/test_diff_harness_generated.py::test_generated_shop_sell_keeper_broke_matches_live_c`
  — live C-oracle differential test; C and Python agree. Skips gracefully when the
  instrumented binary is absent.

## Files Modified

- `src/diff_shim/diffmain.c` — added `__mob_gold=N` and `__mob_silver=N` handlers (+38 lines)
- `tools/diff_harness/pyreplay.py` — added matching Python-side handlers (+16 lines)
- `tools/diff_harness/scenarios/shop_sell_keeper_broke.json` — new scenario (20 lines)
- `tests/test_diff_harness_generated.py` — `test_generated_shop_sell_keeper_broke_matches_live_c` (+39 lines)
- `CHANGELOG.md` — added [2.13.32] Added entries
- `pyproject.toml` — 2.13.31 → 2.13.32

## Test Status

- `pytest tests/ -k "keeper_broke"` — 1 passed, 1 skipped (smoke test skipped; binary present so oracle test ran)
- Full suite: **5452 passed, 5 skipped** (one more than pre-session 5451)

## Next Steps

Cross-file invariant candidates (per `SESSION_STATUS.md`):

1. **Position-transition guards** — does `do_sit`/`do_rest`/`do_stand` correctly gate
   on current position? Probe: read `src/act_move.c` position-check blocks, compare
   to Python `mud/commands/movement.py`; write one failing test for the first missed
   guard, file as INV-NNN if root cause spans modules.
2. **`affect_strip` bitvector-clear contract** — does `affect_strip` in Python correctly
   clear the bitvector flag when removing the last affect of a given type?
3. **Hypothesis state machine extension** — add a `sell_sword_to_broke_keeper` rule to
   `DeterministicNoRngDiffMachine` in `tools/diff_harness/generated.py` to fuzz
   the keeper-broke path alongside the normal sell/buy paths.
