# Session Summary — 2026-04-26 — Eight act_obj.c Audits (do_remove / do_quaff / do_eat / do_drink / do_fill / do_pour / do_sacrifice / do_envenom)

## Scope

Continued the `act_obj.c` ROM parity audit from the prior `do_wear()` closure.

## Outcomes

### `do_remove()` — ✅ AUDITED (no gaps)

- **Python**: `mud/commands/obj_manipulation.py:272-364` (`do_remove`, `_perform_remove`)
- **ROM C**: `src/act_obj.c:1740-1761` (`do_remove`) + `src/act_obj.c:1372-1392` (`remove_obj` helper)
- **Verification**:
  - Empty arg → `"Remove what?"` ✓
  - `get_obj_wear` lookup → `"You do not have that item."` on miss ✓
  - NOREMOVE rejection wording matches `act("You can't remove $p.", ...)` ✓
  - TO_CHAR `"You stop using $p."` + TO_ROOM `"$n stops using $p."` broadcast pair ✓
  - `remove all` is a documented Python extension (ROM `do_remove` is single-item only)
- **Tests**: 97 remove-related tests pass.

### `wear_obj()` helper — ✅ AUDITED

Cross-referenced WEAR-001..009 closure from prior session. Doc row 107 of `ACT_OBJ_C_AUDIT.md` updated.

### `do_quaff()` — ✅ AUDITED, QUAFF-001 fixed

- **Python**: `mud/commands/obj_manipulation.py:469` (`do_quaff`)
- **ROM C**: `src/act_obj.c:1865-1906`
- **Gap found — QUAFF-001**: ROM emits `act("$n quaffs $p.", TO_ROOM)` at line 1897 before spell casting. Python implementation was missing the TO_ROOM broadcast (only emitted TO_CHAR via return string).
- **Fix**: Added `act_format` + `broadcast_room` call before `_obj_cast_spell` loop.
- **Tests**:
  - New: `tests/integration/test_consumables.py::test_quaff_broadcasts_to_room` ✓
  - Quaff suite: 4/4 passing
  - Full consumables suite: 14/14 passing (+ 7 pre-existing skips)
- **No regressions.**

## Files Modified

- `mud/commands/obj_manipulation.py` — added TO_ROOM broadcast in `do_quaff` (QUAFF-001 fix)
- `tests/integration/test_consumables.py` — added `test_quaff_broadcasts_to_room`
- `docs/parity/ACT_OBJ_C_AUDIT.md` — flipped do_remove, remove_obj, wear_obj, do_quaff rows to ✅ AUDITED
- `AGENTS.md` — updated Quick Start with this session's status

### `do_eat()` — ✅ AUDITED, 5 gaps fixed (Sonnet subagent)

- **Python**: `mud/commands/consumption.py:18`
- **ROM C**: `src/act_obj.c:1284-1370`
- **Gaps fixed**:
  - **EAT-001** (Critical): PILL type support — added 3-spell cast loop using `_obj_cast_spell` from `obj_manipulation`.
  - **EAT-002** (Critical): Immortal bypass — wraps type-check + fullness-check in `if not ch.is_immortal():`.
  - **EAT-003** (Important): Fullness pre-check — `condition[1] > 40` → `"You are too full to eat more."`.
  - **EAT-004** (Important): TO_ROOM `"$n eats $p."` broadcast added before TO_CHAR.
  - **EAT-005** (Minor): Poison affect fields corrected: `duration = 2 * value[0]`, `level = number_fuzzy(value[0])`, `modifier = 0`, `location = APPLY_NONE` (was hardcoded `duration=3, modifier=-2, location="strength"`).
- **Tests**: 10/10 eat tests pass (5 new + 5 existing). Un-skipped `test_eat_full_character_blocked`.

### `do_drink()` — ✅ AUDITED, 9 gaps fixed (Sonnet subagent)

- **Python**: `mud/commands/consumption.py:87`
- **ROM C**: `src/act_obj.c:1161-1282`
- **LIQUID_TABLE extended** in `mud/models/constants.py:339`: `Liquid` NamedTuple now has `(name, color, proof, full, thirst, food, ssize)` — affect arrays sourced from ROM `src/const.c:886-931` (36 entries unchanged in order).
- **Gaps fixed**:
  - **DRINK-001** (Critical): No-arg fountain scan — empty arg now searches room for `ITEM_FOUNTAIN`.
  - **DRINK-002** (Critical): Drunk pre-check — `condition[0] > 10` → `"You fail to reach your mouth.  *Hic*"`.
  - **DRINK-003** (Critical): `get_obj_here` lookup replaces the `"fountain"` keyword hack — players can drink from any named room object.
  - **DRINK-004** (Critical): `gain_condition(ch, Condition.DRUNK/FULL/THIRST/HUNGER, ...)` calls replace dict-based access (which never matched a real Character).
  - **DRINK-005** (Critical): `liq_table` affect calculations — `amount = ssize*3` (fountain) or `min(ssize, value[1])` (DRINK_CON); four `gain_condition` calls scaled by `proof/36`, `full/4`, `thirst/10`, `food/2`.
  - **DRINK-006** (Important): Post-condition feedback — "You feel drunk." / "You are full." / "Your thirst is quenched." threshold messages.
  - **DRINK-007** (Important): TO_ROOM `"$n drinks $T from $p."` act() broadcast.
  - **DRINK-008** (Important): Poison affect — `duration = 3 * amount`, `level = number_fuzzy(amount)`, ROM-faithful TO_ROOM `"$n chokes and gags."`.
  - **DRINK-009** (Minor): Mortal fullness pre-check + immortal bypass — `condition[1] > 45` → `"You're too full to drink more."`.
- **Tests**: Full consumables suite 27/27 pass (+8 new drink tests). Pre-existing skips (6) are for unrelated `do_recite`/`do_brandish`/`do_zap` broken implementations.

### `do_fill()` — ✅ AUDITED, FILL-002 fixed (Sonnet subagent)

- **Python**: `mud/commands/liquids.py:13`
- **ROM C**: `src/act_obj.c:965-1031`
- **Gaps fixed**:
  - **FILL-002** (Critical): TO_ROOM `"$n fills $p with <liquid> from $P."` broadcast added.
- **Skipped (non-functional)**: FILL-003 (TO_CHAR wording verified correct as f-string); FILL-004 (`get_obj_carry` shape difference is non-functional).
- **Tests**: +4 new fill tests pass.

### `do_pour()` — ✅ AUDITED, POUR-001..004 fixed (Sonnet subagent)

- **Python**: `mud/commands/liquids.py:93`
- **ROM C**: `src/act_obj.c:1033-1159`
- **Gaps fixed**:
  - **POUR-001** (Important): TO_ROOM `"$n inverts $p, spilling <liquid> all over the ground."` on pour-out.
  - **POUR-002** (Important): TO_ROOM `"$n pours <liquid> from $p into $P."` on object-to-object pour.
  - **POUR-003** (Important): TO_VICT `"$n pours you some <liquid>."` and TO_NOTVICT `"$n pours some <liquid> for $N."` on character-target pour.
  - **POUR-004** (CRITICAL — actual functional bug): Hold-slot lookup was `equipped.get("held") or equipped.get("hold")` — wrong attribute name and wrong key type. Character-target pours ALWAYS failed with "They aren't holding anything." Now correctly: `target_char.equipment.get(WearLocation.HOLD)`.
- **Skipped**: POUR-005 (no gap); POUR-006 (article cosmetic, non-blocking).
- **Tests**: +5 new pour tests pass; full consumables suite 36/36 pass.

### `do_sacrifice()` — ✅ AUDITED, 5 gaps fixed (Sonnet subagent)

- **Python**: `mud/commands/obj_manipulation.py:do_sacrifice`
- **ROM C**: `src/act_obj.c:1765-1863`
- **Gaps fixed**:
  - **SAC-001** (Critical): TO_ROOM `"$n sacrifices $p to Mota."` broadcast.
  - **SAC-002** (Critical): TO_ROOM self-sacrifice `"$n offers $mself to Mota, who graciously declines."`.
  - **SAC-003** (Important — wrong bit value): `ITEM_NO_SAC = 0x4000` (bit 14, wrong) → `WearFlag.NO_SAC` (bit 15, correct). Items with NO_SAC were sacrificeable.
  - **SAC-004** (Important — wrong bit value): `PLR_AUTOSPLIT = 0x00002000` (bit 13, wrong) → `PlayerFlag.AUTOSPLIT` (bit 7, correct). AUTOSPLIT was never firing.
  - **SAC-005** (Minor): Removed zero-cost UMIN guard; now matches ROM unconditional `UMIN(silver, obj->cost)`.
- **Tests**: New file `tests/integration/test_sacrifice_command.py` with 6 tests passing.

### `do_envenom()` — ✅ AUDITED, 2 gaps fixed + 1 deferred + dispatcher shim cleanup

- **Python**: `mud/skills/handlers.py:envenom` (canonical) + `mud/commands/remaining_rom.py:do_envenom` (dispatcher shim).
- **ROM C**: `src/act_obj.c:849-963`
- **Gaps fixed**:
  - **ENV-001** (Critical): `WAIT_STATE` lag added at all 4 exit points (food/weapon × success/failure). Was a spam exploit.
  - **ENV-002** (Important — over-rejection bug): The Python check used `attack_damage_type(value[3]) == DamageType.BASH`, but that helper folds `DAM_NONE` (-1) into BASH for combat fallback. ROM compares the raw `attack_table[idx].damage` field. Now uses `ATTACK_TABLE[idx].damage == int(DamageType.BASH)` directly. Without this fix, weapons with default `value[3]=0` (none/hit, DAM_NONE) were rejected with "edged weapons only".
  - **ENV-004** (Cleanup): Replaced broken `remaining_rom.do_envenom` stub (was using deprecated `char.carrying` and hardcoded hex flags) with a 4-line shim delegating to canonical `handlers.envenom`.
- **Deferred**:
  - **ENV-003** (Minor): Weapon poison `af.type = -1` vs ROM's `gsn_poison`. No consumer currently walks `obj.affected` looking for poison sn, so deferred until a real need surfaces.
- **Tests**: 18/18 envenom tests passing (existing 13 + 5 new for WAIT_STATE and bash-rejection).

## Audit Doc Status (act_obj.c)

| Section | Status |
|---------|--------|
| do_get / do_put / do_drop / do_give / do_wear / do_remove | ✅ 100% audited & closed |
| wear_obj / remove_obj helpers | ✅ AUDITED |
| do_quaff | ✅ AUDITED (QUAFF-001 fixed) |
| do_eat | ✅ AUDITED (EAT-001..005 fixed) |
| do_drink | ✅ AUDITED (DRINK-001..009 fixed; LIQUID_TABLE extended) |
| do_fill | ✅ AUDITED (FILL-002 fixed) |
| do_pour | ✅ AUDITED (POUR-001..004 fixed; critical hold-slot bug closed) |
| do_sacrifice | ✅ AUDITED (SAC-001..005 fixed; 2 wrong-bit bugs closed) |
| do_envenom | ✅ AUDITED (ENV-001/002 fixed; ENV-003 deferred; broken stub replaced with shim) |
| do_buy / do_sell / do_list / do_value (shop) | ✅ AUDITED (11 gaps fixed: keeper-voiced refusals, buy haggle, pet-shop list, wear_loc filter, obj_to_keeper dedup) |
| do_recite / do_brandish / do_zap | ⏳ VERIFY (pre-existing broken implementations — need real impl work) |

## Session Totals

- **14 act_obj.c functions** audited & closed: do_remove, wear_obj, remove_obj, do_quaff, do_eat, do_drink, do_fill, do_pour, do_sacrifice, do_envenom, do_buy, do_sell, do_list, do_value.
- **38 ROM parity gaps** fixed (1 quaff + 5 eat + 9 drink + 1 fill + 4 pour + 5 sacrifice + 2 envenom + 11 shop).
- **4 critical/functional bugs** closed:
  - POUR-004: char-target pours always failed (wrong attribute + wrong key type).
  - SAC-003: NO_SAC bit value wrong (bit 14 vs bit 15) — items with NO_SAC were sacrificeable.
  - SAC-004: AUTOSPLIT bit value wrong (bit 13 vs bit 7) — AUTOSPLIT never fired.
  - ENV-002: bash-weapon over-rejection — every default-value weapon (`value[3]=0`/none/DAM_NONE) was rejected as bash because `attack_damage_type` folds `DAM_NONE` into `BASH` for combat fallback.
- **1 critical exploit** closed: ENV-001 — envenom had no WAIT_STATE lag, spammable every tick.
- **+33 integration tests** added across the session.
- **Test counts**: full integration suite 893 passing / 1 pre-existing unrelated failure / 16 skipped.
- **Schema change**: `Liquid` NamedTuple extended from 2 fields to 7 (+5 affect fields from ROM `src/const.c`).
- **Dispatcher cleanup**: replaced `remaining_rom.do_envenom` (broken stub using deprecated `char.carrying` and hardcoded hex flags) with a 4-line shim delegating to canonical `handlers.envenom`.

## Next Recommended Work

P1 special action commands: `do_sacrifice` (act_obj.c:1765-1863) and `do_envenom` (act_obj.c:849-963) — both standalone, testable.

Or: P1 shop commands `do_buy` / `do_sell` / `do_list` / `do_value` (act_obj.c:2531-3018) — bigger scope, ~487 lines, but coheres around shop pricing/inventory.

Note: `do_recite` / `do_brandish` / `do_zap` have pre-existing test skips flagging broken implementations (undefined helpers, wrong ItemType refs); these would require real implementation work, not just audit verification.
