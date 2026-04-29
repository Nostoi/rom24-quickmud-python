# Session Summary — 2026-04-28 — `healer.c` Audit and Gap Closure

## Scope

Picked the smallest remaining P2 file after `scan.c`: `healer.c`. The ROM C
surface is only one function (`do_heal`), but the Python port was still a
placeholder implementation in `mud/commands/healer.py`: legacy healer lookup,
compressed price-list output, gold-only affordability, no room utterance, and
simplified/non-ROM effect logic. Audited `src/healer.c` end-to-end, identified
four gameplay-visible gaps, and closed all four with ROM-focused integration
coverage.

## Outcomes

### `HEALER-001` — ✅ FIXED

- **Python**: `mud/commands/healer.py:149-177`
- **ROM C**: `src/healer.c:49-79`
- **Gap**: Healer lookup ignored `ACT_IS_HEALER`, and the no-arg command returned a compressed summary instead of the ROM service table.
- **Fix**: Restored `ActFlag.IS_HEALER` lookup (with legacy fallback retained for compatibility) and emitted the exact ROM-style service list, including the `serious` display quirk and `critic`/`blind` labels.
- **Tests**: `tests/integration/test_healer_command_parity.py::test_heal_lists_rom_price_table_for_act_is_healer` — passing.

### `HEALER-002` — ✅ FIXED

- **Python**: `mud/commands/healer.py:179-201`
- **ROM C**: `src/healer.c:147-190`
- **Gap**: `mana` service ignored total silver-equivalent wealth, skipped `deduct_cost`, skipped healer payout and TO_ROOM utterance, and used a flat restore amount.
- **Fix**: Added ROM-style prefix/alias matching, silver-aware affordability (`gold * 100 + silver`), `deduct_cost`, healer gold/silver payout, TO_ROOM utterance broadcast, and `rng_mm.dice(2, 8) + c_div(level, 3)` mana restoration.
- **Tests**: `tests/integration/test_healer_command_parity.py::test_heal_mana_uses_total_wealth_rom_formula_and_room_utterance` — passing.

### `HEALER-003` — ✅ FIXED

- **Python**: `mud/commands/healer.py:56-78,203-205`
- **ROM C**: `src/healer.c:156-160,196`
- **Gap**: `refresh` bypassed the underlying spell and jumped directly to a placeholder full restore.
- **Fix**: Routed `refresh` through the existing ROM-backed `spell_refresh` handler with the healer mob as caster, preserving ROM movement gain and message text.
- **Tests**: `tests/integration/test_healer_command_parity.py::test_heal_refresh_uses_spell_refresh_not_full_restore` — passing.

### `HEALER-004` — ✅ FIXED

- **Python**: `mud/commands/healer.py:56-78,203-205`
- **ROM C**: `src/healer.c:107-112,196`
- **Gap**: `heal` bypassed the underlying spell and always filled the target to max hit points.
- **Fix**: Routed `heal` through the existing ROM-backed `spell_heal` handler with the healer mob as caster, preserving the fixed 100-point healing behavior and ROM messaging.
- **Tests**: `tests/integration/test_healer_command_parity.py::test_heal_spell_uses_rom_heal_amount_not_full_heal` — passing.

## Files Modified

- `mud/commands/healer.py` — replaced placeholder logic with ROM-style healer detection, service matching, silver-aware pricing, utterance broadcast, mana formula, and real spell dispatch.
- `tests/integration/test_healer_command_parity.py` — new integration parity coverage for the four healer gaps.
- `tests/test_healer.py` — updated legacy expectations to ROM-faithful price-list and spell messages.
- `tests/test_healer_parity.py` — updated stale `refresh` expectation to match ROM spell messaging.
- `docs/parity/HEALER_C_AUDIT.md` — new audit doc with Phase 1-5 completion.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — flipped `healer.c` from ❌ Not Audited to ✅ AUDITED.
- `docs/sessions/SESSION_STATUS.md` — advanced current-state pointer from `scan.c` to `healer.c`.
- `CHANGELOG.md` — added `[Unreleased]` `HEALER-001`..`004` entries.

## Test Status

- `pytest tests/integration/test_healer_command_parity.py tests/test_healer.py tests/test_healer_parity.py tests/test_healer_rom_parity.py -q` — `23/23` passing.
- Full suite not re-run this session.

## Next Steps

`healer.c` is closed. The next smallest P2 target is `alias.c` (0%, command
alias system). After that, the remaining obvious P2 candidates are larger:
`act_wiz.c` (40% Partial), `special.c` (40% Not Audited), and `board.c`
(35% Not Audited).
