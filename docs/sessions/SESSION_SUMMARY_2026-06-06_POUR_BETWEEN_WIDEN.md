# Session Summary — 2026-06-06 — Diff-Harness Phase C Widening: Pour Between Containers (2.13.16)

## Scope

Picked up from SESSION_STATUS "Next Intended Task — Pour between containers."
Added `pour <source> <target>` (transfer liquid between two drink containers)
to the `DeterministicNoRngDiffMachine`, exercising the full `do_pour` transfer
path against the C oracle.

## Outcomes

### Pour Between Containers — ✅ ADDED

- **Python**: `tools/diff_harness/generated.py` — `coffee_cup` `_ObjectState` (vnum 3101), 4 new rules
- **ROM C**: `src/act_obj.c:1033-1159` (`do_pour`) — lines 1100-1135 pour-transfer path
- **Implementation**: Added coffee cup object (vnum 3101, keywords `coffee cup`,
  capacity 6, drink container) with load/get/pour-out/pour-between rules. The
  `pour_bottle_into_cup` rule transfers beer from the bottle (16 sips) into an
  empty cup (capacity 6): ROM's liquid-type guard is skipped (target is empty),
  amount = min(16, 6-0) = 6 sips, liquid type copied from source to target.
- **Tests**: `test_generated_pour_between_containers_matches_live_c` — live C-oracle test

## Files Modified

- `tools/diff_harness/generated.py` — `coffee_cup` `_ObjectState` + 4 new rules (load_coffee_cup, get_coffee_cup, pour_out_coffee_cup, pour_bottle_into_cup)
- `tests/test_diff_harness_generated.py` — 1 new C-oracle test
- `CHANGELOG.md` — 2.13.16 section
- `pyproject.toml` — 2.13.15 → 2.13.16

## Test Status

- Diff harness: **33/33 passing** (7 smoke + 13 unit + 13 generated, +1 new)
- `ruff check .` clean

## Next Steps

1. Continue Phase C deterministic diff-harness widening:
   - **Full drink logic** — requires lowering `condition[FULL]` in both C and
     Python drivers so the actual sip-decrement + condition-gain path is
     exercised. The Python side (`tools/diff_harness/pyreplay.py`) already
     handles `__cond_full=` and `__cond_thirst=` meta-commands; the C shim
     (`src/diff_shim/diffmain.c`) needs two ~5-line `strncmp` handlers after
     the `__silver=` block, then a rebuild (`cd src && make -f Makefile.diffshim
     diffshim`).
2. Add RNG-locked combat scenarios only after seed alignment is proven.
