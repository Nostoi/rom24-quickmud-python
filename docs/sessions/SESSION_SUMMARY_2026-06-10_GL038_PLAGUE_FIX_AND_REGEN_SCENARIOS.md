# Session Summary — 2026-06-10 — GL-038 PLAGUE Fix + Regen Scenarios (PLAGUE/SLOW/Room Rates)

## Scope

Continuation from v2.13.78 (`char_update_regen_poison` and `char_update_regen_haste` diff-harness
scenarios complete, `__add_affect=<bit>` meta-command in place). This session addressed the three
remaining `char_update` regen coverage candidates: the AFF_PLAGUE parity bug (deferred last session
due to "orphan-bit divergence"), the AFF_SLOW divisor scenario, and the `heal_rate`/`mana_rate`
room-multiplier scenario. A parity bug was found and fixed (GL-038) before authoring the PLAGUE
scenario, and two new meta-commands were added to the diff harness for room-rate probing.

## Outcomes

### GL-038 PLAGUE tick gate used bitmask instead of spell-affect list — ✅ FIXED

- **Python**: `mud/game_loop.py:731` — `_char_update_tick_effects`
- **ROM C**: `src/update.c:793` — `if (is_affected(ch, gsn_plague))`
- **Root cause**: Python gated the plague tick on `has_affect(AffectFlag.PLAGUE)` (bitmask check
  via `affected_by & flag`) rather than ROM's `is_affected(ch, gsn_plague)` which scans the
  **spell affect list**. A character with innate `AFF_PLAGUE` in `affected_by` but no spell-affect
  entry (e.g. area-file `affected_by` assignment, or `__add_affect`) would in Python: enter the
  plague tick block, print writhe messages, find no spell entry, and **clear the bitmask** — losing
  the ÷8 regen divisor after pulse 1. In C: the block was never entered (`is_affected` returns
  false), the bitmask persisted, and regen ÷8 applied every pulse. Reachable in normal play via
  area-file mobs with innate PLAGUE.
- **Fix**: Changed the plague tick gate from `has_affect(AffectFlag.PLAGUE)` to a spell-list scan
  (`for af in character.affected: if spell_name == "plague": plague_af = af`). Removed the
  unreachable orphan-bit clearing branch (lines 748-751 in the old code). Writhe messages now
  print only when a spell affect entry exists, matching C. Regen divisors in `hit_gain`/`mana_gain`/
  `move_gain` (lines 221-226) remain on `has_affect` (bitmask) — the asymmetry is intentional:
  ROM uses `IS_AFFECTED` (bitmask) for regen divisors and `is_affected` (list) for the tick gate.
- **Tests**: `test_drive_python_replay_plague_affect_divides_regen_by_eight` (new) +
  smoke scenario `char_update_regen_plague` — both confirm the fix. Also `tests/integration/
  test_gl_024_level1_plague_dormant.py` and `tests/test_game_loop.py` — still green.
- **Filed**: GL-038 row added to `docs/parity/UPDATE_C_AUDIT.md`.

### `char_update_regen_plague` diff-harness scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_plague.json` — mage (class 0),
  level 5, SLEEPING (position=4), HP=1/mana=5/move=5, `__add_affect=8388608` (AFF_PLAGUE = 1<<23),
  three `__char_update` pulses.
- **C oracle**: AFF_PLAGUE bitmask persists across all three pulses (tick never fires — no spell
  entry). Regen ÷8 each pulse:
  - HP: 1 → 2 → 3 → 4 (+1/pulse; base 10 // 8 = 1)
  - Mana: 5 → 7 → 9 → 11 (+2/pulse; base 17 // 8 = 2)
  - Move: 5 → 8 → 11 → 14 (+3/pulse; base 28 // 8 = 3)
- **Golden**: `tests/data/golden/diff/char_update_regen_plague.golden.json` (8 steps, C sha f4406280).

### `char_update_regen_slow` diff-harness scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_slow.json` — same setup,
  `__add_affect=536870912` (AFF_SLOW = 1<<29), three `__char_update` pulses.
- **C oracle**: AFF_SLOW bitmask persists (no tick side-effects for SLOW). Same ÷2 branch as HASTE
  (ROM `src/update.c:280-282`):
  - HP: 1 → 6 → 11 → 16 (+5/pulse; base 10 // 2 = 5)
  - Mana: 5 → 13 → 21 → 29 (+8/pulse; base 17 // 2 = 8)
  - Move: 5 → 19 → 33 → 47 (+14/pulse; base 28 // 2 = 14)
- **Golden**: `tests/data/golden/diff/char_update_regen_slow.golden.json` (8 steps).
- **Note**: Numerically identical to the HASTE scenario — same ÷2 branch, different flag.

### `char_update_regen_room_rates` diff-harness scenario — ✅ ADDED

- **New meta-commands**:
  - `__set_heal_rate=N` — sets `room->heal_rate` (both C shim and Python). Scales `hit_gain`
    and `move_gain` via `gain * heal_rate / 100` (ROM `src/update.c:215, 326`).
  - `__set_mana_rate=N` — sets `room->mana_rate`. Scales `mana_gain` ONLY via
    `gain * mana_rate / 100` (ROM `src/update.c:297`).
- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_room_rates.json` — SLEEPING mage,
  `__set_heal_rate=50` and `__set_mana_rate=200`, three `__char_update` pulses.
- **C oracle**: Confirms the asymmetry — `heal_rate` scales HP+move, `mana_rate` scales only mana:
  - HP: 1 → 6 → 11 → 16 (+5/pulse; base 10 * 50/100 = 5)
  - Mana: 5 → 39 → 73 → 100 (+34/pulse, capped at max_mana=100 on pulse 3; base 17 * 200/100 = 34)
  - Move: 5 → 19 → 33 → 47 (+14/pulse; base 28 * 50/100 = 14)
- **Golden**: `tests/data/golden/diff/char_update_regen_room_rates.golden.json` (9 steps).
- **Python already correct**: no parity bug found.

### Unit tests — ✅ ADDED

- `test_drive_python_replay_plague_affect_divides_regen_by_eight` — verifies HP=2/mana=7/move=8
  after one pulse with orphan AFF_PLAGUE bit; asserts flag still set.
- `test_drive_python_replay_slow_affect_halves_regen_by_two` — verifies HP=6/mana=13/move=19
  after one pulse with AFF_SLOW bit.
- `test_drive_python_replay_room_rates_heal_and_mana_independent` — verifies HP=6/mana=39/move=19
  after one pulse with heal_rate=50 and mana_rate=200.

## Files Modified

- `mud/game_loop.py` — GL-038 fix: plague tick gate changed from bitmask to spell-list scan;
  orphan-bit clearing removed (lines 730-807 restructured)
- `src/diff_shim/diffmain.c` — `__set_heal_rate=N` and `__set_mana_rate=N` meta-commands (20 lines)
- `tools/diff_harness/pyreplay.py` — `__set_heal_rate=N` and `__set_mana_rate=N` handlers (20 lines)
- `tools/diff_harness/scenarios/char_update_regen_plague.json` — new scenario
- `tools/diff_harness/scenarios/char_update_regen_slow.json` — new scenario
- `tools/diff_harness/scenarios/char_update_regen_room_rates.json` — new scenario
- `tests/data/golden/diff/char_update_regen_plague.golden.json` — C oracle (8 steps)
- `tests/data/golden/diff/char_update_regen_slow.golden.json` — C oracle (8 steps)
- `tests/data/golden/diff/char_update_regen_room_rates.golden.json` — C oracle (9 steps)
- `tests/test_diff_harness_unit.py` — three new unit tests (105 lines)
- `docs/parity/UPDATE_C_AUDIT.md` — GL-038 row added; integration test table updated
- `CHANGELOG.md` — [2.13.79] Fixed/Added + [2.13.80] Added entries
- `pyproject.toml` — 2.13.78 → 2.13.80

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — **65/65 passing**
  (was 59; +3 smoke scenarios, +3 unit tests, +1 regen_slow/plague from SLOW/PLAGUE unit tests)
- Full suite: **5544 passed, 4 skipped** (was 5538; +6 new tests)

## Affect Penalty Regen Coverage Summary

| AFF_* flag | Divisor | Regen code path | Tick gate | C-oracle scenario |
|------------|---------|----------------|-----------|------------------|
| AFF_POISON (4096) | ÷4 | `game_loop.py:221` | bitmask only (no tick damage without spell entry) | `char_update_regen_poison` |
| AFF_PLAGUE (8388608) | ÷8 | `game_loop.py:223` | spell-list (GL-038 fixed) — orphan bit: tick never fires | `char_update_regen_plague` |
| AFF_HASTE (2097152) | ÷2 | `game_loop.py:225` | no tick for HASTE | `char_update_regen_haste` |
| AFF_SLOW (536870912) | ÷2 | `game_loop.py:225` | no tick for SLOW | `char_update_regen_slow` |
| Room heal_rate | × rate/100 (HP+move) | `game_loop.py:211, 326` | N/A | `char_update_regen_room_rates` |
| Room mana_rate | × rate/100 (mana only) | `game_loop.py:281` | N/A | `char_update_regen_room_rates` |

## Next Steps

Cross-file invariants remains the active pass. Concrete candidates:

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **Furniture bonus scenario**: SLEEPING PC on furniture with nonzero `value[3]`/`value[4]`
   — no existing furniture objects with non-100 values in game data; would need a `__oload` +
   `__set_on=` meta-command to set `char.on` to a furniture object. Requires designing the
   `__set_on` meta-command for both pyreplay.py and diffmain.c.

3. **Next cross-INV candidate** — probe affect-tick contracts or position-transition edges for
   divergences not yet covered by an INV row. Candidates: affect-tick timing, position-transition
   sequencing, group/follower chain. Method: pick a candidate, run 5-minute probe (ROM C contract
   → Python equivalent → one failing test), then either gap-closer commit or new INV-NNN.
