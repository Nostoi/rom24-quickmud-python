# Session Summary — 2026-06-10 — Furniture Regen Scenario + __set_on Meta-Commands

## Scope

Continuation from v2.13.80 (`GL-038` fixed, all AFF_* regen scenarios covered,
`__set_heal_rate`/`__set_mana_rate` in place). The remaining candidate from the previous
session was the **furniture sitting bonus scenario** — a SLEEPING PC sitting on furniture
with custom `value[3]`/`value[4]` multipliers. No existing game-data furniture has non-zero
values, so this required three new meta-commands (`__set_on=`, `__set_on_val3=`,
`__set_on_val4=`) before the scenario could be authored. The C oracle confirmed Python already
implements the furniture branches correctly. Session ends at v2.13.81.

## Outcomes

### `__set_on=<vnum>`, `__set_on_val3=<n>`, `__set_on_val4=<n>` meta-commands — ✅ ADDED

- **Harness files**: `src/diff_shim/diffmain.c` and `tools/diff_harness/pyreplay.py`
- **ROM C**: `src/update.c:217-218` (hit_gain), `:299-300` (mana_gain), `:350-351` (move_gain)
- **What they do**:
  - `__set_on=<vnum>` — spawns a furniture object with the given vnum via `create_object` /
    `spawn_object`, places it in the test room via `obj_to_room` / `room.add_object`, and
    sets `ch->on` / `char.on` to it.
  - `__set_on_val3=<n>` — sets `ch->on->value[3]` (furniture HP/move bonus percent).
  - `__set_on_val4=<n>` — sets `ch->on->value[4]` (furniture mana bonus percent).
- **Parity note (Python side)**: `spawn_object` does NOT auto-sync `value` from the prototype
  (documented in AGENTS.md). The Python `__set_on` handler explicitly copies `prototype.value`
  to a length-5 list before returning — mirroring C's `create_object` clean copy — so that
  `__set_on_val3/4` overrides start from the same baseline as C. Without this, C starts from
  prototype 0-values and Python silently falls back to the `[100,100,100,100,100]` fallback in
  `hit_gain`/`move_gain`/`mana_gain`.

### `char_update_regen_furniture` diff-harness scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_furniture.json` — L5 Tester,
  SLEEPING (position=4), HP=1/mana=5/move=5, bench (vnum 3134), `value[3]=150`, `value[4]=200`,
  three `__char_update` pulses.
- **Asymmetric multipliers**: `value[3]=150 ≠ value[4]=200` is intentional — a value-index swap
  (move using `[4]`, mana using `[3]`) would produce different numbers, making the bug detectable.
  ROM uses `value[3]` for both HP and move (same multiplier), and `value[4]` for mana only.
- **C oracle** (seed 12345):
  - HP: 1 → 16 → 20 → 20 (+15/pulse until cap; base 10 * 150/100 = 15)
  - Mana: 5 → 39 → 73 → 100 (+34/pulse until cap; base 17 * 200/100 = 34)
  - Move: 5 → 47 → 89 → 100 (+42/pulse until cap; base 28 * 150/100 = 42)
- **Golden**: `tests/data/golden/diff/char_update_regen_furniture.golden.json` (11 steps).
- **Result**: Python already correct — no parity bug found. Scenario locks the contract.

### `test_drive_python_replay_furniture_bonus_scales_regen` — ✅ ADDED

- **File**: `tests/test_diff_harness_unit.py`
- Verifies HP=16/mana=39/move=47 after one pulse with value[3]=150, value[4]=200 SLEEPING L5.
- Documents that HP and move both scale by value[3], mana by value[4] (easy-to-miss ROM detail).

## Files Modified

- `src/diff_shim/diffmain.c` — `__set_on=`, `__set_on_val3=`, `__set_on_val4=` meta-commands (+38 lines)
- `tools/diff_harness/pyreplay.py` — matching Python handlers with prototype-value-copy logic (+36 lines)
- `tools/diff_harness/scenarios/char_update_regen_furniture.json` — new scenario (11 steps)
- `tests/data/golden/diff/char_update_regen_furniture.golden.json` — C oracle golden (11 steps)
- `tests/test_diff_harness_unit.py` — `test_drive_python_replay_furniture_bonus_scales_regen` (+41 lines)
- `CHANGELOG.md` — `[2.13.81]` Added entries
- `pyproject.toml` — 2.13.80 → 2.13.81

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — **67/67 passing**
  (was 65; +1 smoke scenario (furniture), +1 unit test (furniture bonus))
- Full suite: **5546 passed, 4 skipped** (was 5544; +2 new tests)

## Regen Scenario Coverage Summary (complete after this session)

| Branch | Multiplier | Code path | C-oracle scenario |
|--------|-----------|-----------|------------------|
| AFF_POISON | ÷4 | `game_loop.py:221` | `char_update_regen_poison` |
| AFF_PLAGUE (orphan bit) | ÷8 | `game_loop.py:223` | `char_update_regen_plague` |
| AFF_HASTE | ÷2 | `game_loop.py:225` | `char_update_regen_haste` |
| AFF_SLOW | ÷2 | `game_loop.py:225` | `char_update_regen_slow` |
| Room `heal_rate` | × rate/100 (HP + move) | `game_loop.py:211, 326` | `char_update_regen_room_rates` |
| Room `mana_rate` | × rate/100 (mana only) | `game_loop.py:281` | `char_update_regen_room_rates` |
| Furniture `value[3]` | × val/100 (HP + move) | `game_loop.py:219, 334` | `char_update_regen_furniture` ✅ NEW |
| Furniture `value[4]` | × val/100 (mana only) | `game_loop.py:288` | `char_update_regen_furniture` ✅ NEW |

## Next Steps

Cross-file invariants remains the active pass. Regen scenario suite is now complete.

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **Next cross-INV candidate** — probe affect-tick contracts, position-transition edges, or
   group/follower chain for divergences not yet covered by an INV row.
   Method: pick a candidate, 5-minute probe (ROM C contract → Python equivalent → one failing test),
   then either gap-closer commit or new INV-NNN in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.
   The next free INV ID is INV-042.
