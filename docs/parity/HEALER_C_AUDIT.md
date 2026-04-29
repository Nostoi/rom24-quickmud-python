# `healer.c` Audit — ROM 2.4b6 → QuickMUD-Python Parity

**Status:** ✅ AUDITED — all 4 gameplay-visible gaps closed (`HEALER-001`..`HEALER-004`)
**Date:** 2026-04-28
**ROM C:** `src/healer.c` (157 lines, 1 function)
**Python:** `mud/commands/healer.py`
**Priority:** P2 (service command, economy-visible and gameplay-visible)

## Phase 1 — Function Inventory

| ROM C function | ROM lines | Python equivalent | Status |
|----------------|-----------|-------------------|--------|
| `do_heal` | `src/healer.c:41-197` | `mud/commands/healer.py:165-205` | ✅ AUDITED |

## Phase 2 — Line-by-line Verification

### `do_heal` — healer detection and price list

ROM `src/healer.c:49-80`:
- Scans room occupants and selects the first NPC with `ACT_IS_HEALER`.
- Rejects with `"You can't do that here."` if none exists.
- For empty args, emits the full 10-line price list, including the ROM display quirk where `serious` shows `15 gold` while the actual cost is `1600` silver.

Python before closure:
- ❌ Looked only for legacy `spec_healer` / `is_healer` markers, not `ACT_IS_HEALER`.
- ❌ Returned a compressed summary string instead of the ROM price table.

Python now:
- ✅ Detects healer NPCs via `ActFlag.IS_HEALER`, with legacy fallback retained for compatibility while data/tests transition.
- ✅ Returns the ROM-faithful service list and prompt text.

### `do_heal` — service matching and economic checks

ROM `src/healer.c:83-176`:
- Uses `str_prefix()` for ROM-style abbreviations and aliases (`critic`, `curse`, `energize`, `moves`, etc.).
- Checks total wealth with `ch->gold * 100 + ch->silver`.
- Refuses service if total coin value is insufficient.

Python before closure:
- ❌ Required simplified exact keys and missed ROM aliases like `blind`, `energize`, and `moves`.
- ❌ Checked `char.gold` only, ignoring `silver`.

Python now:
- ✅ Uses ROM-style prefix matching across canonical service names and aliases.
- ✅ Checks total silver-equivalent wealth and charges in silver.

### `do_heal` — wait state, payment, and utterance

ROM `src/healer.c:178-183`:
- Applies `WAIT_STATE(ch, PULSE_VIOLENCE)`.
- Calls `deduct_cost(ch, cost)`.
- Pays the healer mob in gold and silver.
- Emits `act("$n utters the words '$T'.", mob, NULL, words, TO_ROOM);`

Python before closure:
- ❌ No wait state.
- ❌ Deducted only whole gold.
- ❌ Did not pay the healer mob.
- ❌ Did not emit the room utterance.

Python now:
- ✅ Applies ROM wait-state semantics.
- ✅ Uses `mud.handler.deduct_cost`.
- ✅ Credits the healer mob in gold/silver.
- ✅ Broadcasts the spoken words to the room.

### `do_heal` — spell dispatch and mana restoration

ROM `src/healer.c:185-196`:
- `mana` is a special-case non-spell: `dice(2, 8) + mob->level / 3`, capped at `max_mana`.
- All other services call the underlying ROM spell implementation with healer level as caster level.

Python before closure:
- ❌ Used placeholder full-heal/flat-heal logic.
- ❌ `mana` restored a flat `10`.
- ❌ `refresh` jumped directly to full movement.

Python now:
- ✅ Uses real spell handlers (`cure_light`, `cure_serious`, `cure_critical`, `heal`, `refresh`, `cure_blindness`, `cure_disease`, `cure_poison`, `remove_curse`) with the healer mob as caster.
- ✅ Uses ROM mana formula with `rng_mm.dice(2, 8)` and `c_div(level, 3)`.
- ✅ Preserves ROM spell messaging as the command result.

## Phase 3 — Gaps

| ID | Severity | ROM C ref | Python ref | Description | Status |
|----|----------|-----------|------------|-------------|--------|
| `HEALER-001` | CRITICAL | `src/healer.c:49-79` | `mud/commands/healer.py` (pre-fix) | Healer lookup ignored `ACT_IS_HEALER`, and the no-arg branch emitted a non-ROM summary string instead of the ROM price table. | ✅ FIXED — `tests/integration/test_healer_command_parity.py::test_heal_lists_rom_price_table_for_act_is_healer` |
| `HEALER-002` | CRITICAL | `src/healer.c:147-190` | `mud/commands/healer.py` (pre-fix) | `mana` handling ignored total wealth in silver, skipped `deduct_cost`, skipped TO_ROOM utterance, and used a flat mana restore instead of `dice(2,8) + level/3`. | ✅ FIXED — `tests/integration/test_healer_command_parity.py::test_heal_mana_uses_total_wealth_rom_formula_and_room_utterance` |
| `HEALER-003` | IMPORTANT | `src/healer.c:156-160,196` | `mud/commands/healer.py` (pre-fix) | `refresh` used placeholder full-restore logic instead of the underlying ROM spell behavior. | ✅ FIXED — `tests/integration/test_healer_command_parity.py::test_heal_refresh_uses_spell_refresh_not_full_restore` |
| `HEALER-004` | IMPORTANT | `src/healer.c:107-112,196` | `mud/commands/healer.py` (pre-fix) | `heal` used placeholder “fill to max” logic instead of the underlying ROM `spell_heal` fixed 100-point restoration. | ✅ FIXED — `tests/integration/test_healer_command_parity.py::test_heal_spell_uses_rom_heal_amount_not_full_heal` |

## Phase 4 — Closures

### `HEALER-001` — ✅ FIXED

- **Python:** `mud/commands/healer.py:149-177`
- **ROM C:** `src/healer.c:49-79`
- **Fix:** Restored `ACT_IS_HEALER` detection and ROM-faithful service-list output.
- **Tests:** `tests/integration/test_healer_command_parity.py::test_heal_lists_rom_price_table_for_act_is_healer`

### `HEALER-002` — ✅ FIXED

- **Python:** `mud/commands/healer.py:179-201`
- **ROM C:** `src/healer.c:147-190`
- **Fix:** Added silver-aware affordability, `deduct_cost`, healer payout, TO_ROOM utterance, and ROM mana restoration formula.
- **Tests:** `tests/integration/test_healer_command_parity.py::test_heal_mana_uses_total_wealth_rom_formula_and_room_utterance`

### `HEALER-003` — ✅ FIXED

- **Python:** `mud/commands/healer.py:56-78,203-205`
- **ROM C:** `src/healer.c:156-160,196`
- **Fix:** Routed `refresh` through the underlying spell handler instead of placeholder max-fill logic.
- **Tests:** `tests/integration/test_healer_command_parity.py::test_heal_refresh_uses_spell_refresh_not_full_restore`

### `HEALER-004` — ✅ FIXED

- **Python:** `mud/commands/healer.py:56-78,203-205`
- **ROM C:** `src/healer.c:107-112,196`
- **Fix:** Routed `heal` through the underlying spell handler instead of placeholder full-heal logic.
- **Tests:** `tests/integration/test_healer_command_parity.py::test_heal_spell_uses_rom_heal_amount_not_full_heal`

## Phase 5 — Completion

✅ `healer.c` is fully audited.

- Command lookup now mirrors ROM healer detection and prefix behavior.
- Economic handling now mirrors ROM silver/gold semantics.
- Spell effects now delegate to the real ROM-backed spell handlers.
- Healer-focused regression coverage is in place across integration and unit tests.

Validation:
- `pytest tests/integration/test_healer_command_parity.py tests/test_healer.py tests/test_healer_parity.py tests/test_healer_rom_parity.py -q` — `23 passed`
