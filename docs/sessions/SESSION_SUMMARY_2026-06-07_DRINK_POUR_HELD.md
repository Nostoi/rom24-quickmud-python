# Session Summary — 2026-06-07 — Diff-Harness Phase C Widening: Full Drink + Pour Into Held Container (2.13.17)

## Scope

Picked up from SESSION_STATUS "Next Intended Task — Full drink logic + Pour into held container."
Added `__cond_full=`, `__cond_thirst=`, and `__mob_hold=` C-shim meta-commands, rebuilt
the binary, and widened the `DeterministicNoRngDiffMachine` to exercise the actual
drinking path (sip decrement, condition gains) and the vch branch of `do_pour` (pour
into a character's held container). Also fixed a snapshot inventory filter divergence.

## Outcomes

### Full Drink Logic — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c` — `__cond_full=<n>` and `__cond_thirst=<n>` handlers
- **Python**: `tools/diff_harness/pyreplay.py:74-83` — already existed
- **Implementation**: `drink_bottle_beer` state-machine rule now inserts `__cond_full=0`
  before `drink bottle`, bypassing the fullness guard so the actual drinking path
  (sip decrement, condition gains, liquid effects) is exercised against the C oracle.
  Previously only the fullness-guard rejection was tested.
- **C binary**: rebuilt with `make -f Makefile.diffshim diffshim`

### Pour Into Held Container — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c` — `__mob_hold=<vnum>` handler (create empty
  drink container, equip to first NPC's HOLD slot)
- **Python**: `tools/diff_harness/pyreplay.py` — `__mob_hold=` handler with MobInstance
  inventory + equipment setup
- **State machine**: `give_drunk_empty_cup` + `pour_bottle_into_drunk_held_cup` rules
  in `tools/diff_harness/generated.py`
- **ROM C**: `src/act_obj.c:1146-1157` — vch branch of `do_pour` (TO_CHAR/TO_VICT/TO_NOTVICT messages)
- **Test**: `test_generated_pour_into_held_container_matches_live_c` — live C-oracle test

### Snapshot Inventory Filter Fix — ✅ FIXED

- **Python**: `tools/diff_harness/pysnap.py` — new `_is_equipped` helper filters
  equipped items from `_char_snap` inventory list, matching the C shim's
  `obj->wear_loc != WEAR_NONE` gate (`src/diff_shim/diffmain.c:292-293`)

## Files Modified

- `src/diff_shim/diffmain.c` — `__cond_full=`, `__cond_thirst=`, `__mob_hold=` handlers
- `tools/diff_harness/pyreplay.py` — `__mob_hold=` handler
- `tools/diff_harness/generated.py` — `_drunk_has_empty_cup` flag + 3 new rules (give_drunk_empty_cup, pour_bottle_into_drunk_held_cup, drink_bottle_beer updated)
- `tools/diff_harness/pysnap.py` — `_is_equipped` helper + inventory filter
- `tests/test_diff_harness_generated.py` — 1 new C-oracle test
- `CHANGELOG.md` — 2.13.17 section
- `pyproject.toml` — 2.13.16 → 2.13.17

Also staged previous session's uncommitted work:
- `CHANGELOG.md` — 2.13.16 section (pour between containers)
- `pyproject.toml` — 2.13.15 → 2.13.16
- `docs/sessions/SESSION_SUMMARY_2026-06-06_POUR_BETWEEN_WIDEN.md` (new)

## Test Status

- Diff harness: **34/34 passing** (14 generated + 7 smoke + 13 unit)
- Full suite: **5424 passed, 10 pre-existing failures, 4 skipped**
- `ruff check .` clean

## Next Steps

1. Continue Phase C deterministic diff-harness widening:
   - **Conform to known surface** — the previous session's pour-out/pour-between + this
     session's drink/pour-held close the liquid/drink surface for the deterministic
     harness (no RNG). No state-machine rules remain deferred on this surface.
   - **RNG-locked combat scenarios** only after seed alignment is proven.
   - **Continue cross-INV probe-then-scope** as the active pass mode.
