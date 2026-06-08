# Session Summary — 2026-06-08 — Hypothesis broke-keeper sell rules

## Scope

Short focused session. Picked up candidate #3 from the previous session's
`SESSION_STATUS.md` "Next Intended Task": extend `DeterministicNoRngDiffMachine`
in `tools/diff_harness/generated.py` with a `sell_sword_to_broke_keeper` rule so
Hypothesis can fuzz the keeper-broke sell-error path alongside the existing
sell/buy paths. Probed candidates #1 (position-transition guards) and #2
(`affect_strip` bitvector-clear) and found both already fully covered.

## Outcomes

### `zero_keeper_wealth` + `sell_sword_to_broke_keeper` Hypothesis rules — ✅ ADDED

- **Python**: `tools/diff_harness/generated.py`
- **ROM C**: `src/act_obj.c:2916-2921` (wealth-check early exit)
- **Fix**: Two new `@rule` methods added to `DeterministicNoRngDiffMachine`:
  - `zero_keeper_wealth`: emits `__mob_gold=0` + `__mob_silver=0`; gates on
    keeper loaded and `not self._keeper_is_broke`; sets `_keeper_is_broke = True`.
  - `sell_sword_to_broke_keeper`: emits bare `sell sword` (no `__seed` brackets
    — the wealth check at `src/act_obj.c:2916-2921` fires before the
    `number_percent()` call at line 2925, so no RNG is consumed on this path);
    sword stays in inventory on failure; wealth unchanged.
  - `sell_sword_to_weaponsmith` gains `not self._keeper_is_broke` precondition
    so the successful and failed sell paths are mutually exclusive.
- **State tracking**: new `_keeper_is_broke: bool = False` field in `__init__`;
  complements existing `_keeper_has_sword` for buy-side state.
- **Tests**: 3 generated shop tests passing (`test_generated_shop_sell_matches_live_c`,
  `test_generated_shop_buy_matches_live_c`,
  `test_generated_shop_sell_keeper_broke_matches_live_c`).

### Position-transition guards probe — ✅ CLEAN (no gap)

Probed `mud/commands/position.py` vs `src/act_move.c:999-1492`. Python `do_sit`,
`do_rest`, `do_stand`, `do_sleep`, `do_wake` all gate correctly on current
position. Existing `tests/integration/test_position_commands.py` (40 tests) and
`INV-016` enforcement cover the broadcast contract. No gap filed.

### `affect_strip` bitvector-clear probe — ✅ CLEAN (no gap)

Probed `mud/handler.py:affect_remove` + `affect_check` vs
`src/handler.c:1317-1358 affect_remove` + `1182-1228 affect_check`. Python
mirrors ROM's "REMOVE_BIT then re-scan remaining affects + equipped items to
conditionally SET_BIT back" contract exactly. `tests/test_handler_affects_rom_parity.py`
(27 tests, all passing) already covers the full lifecycle including bitvector
clearing. No gap filed.

## Files Modified

- `tools/diff_harness/generated.py` — `_keeper_is_broke` field; `zero_keeper_wealth`
  and `sell_sword_to_broke_keeper` rules; `sell_sword_to_weaponsmith` precondition guard
- `CHANGELOG.md` — added [2.13.33] Added entry
- `pyproject.toml` — 2.13.32 → 2.13.33
- `.claude/skills/rom-session-handoff/SKILL.md` — minor README-surfaces note (pre-existing M)

## Test Status

- `pytest tests/ -k "generated_shop"` — 3 passed
- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — 23 passed, 1 skipped
- Full suite: **5448 passed, 5 skipped** (5453 collected)

## Next Steps

Cross-file invariant candidates still to probe:

1. **INV-025 follow-up** — broader `_push_message`/`broadcast_room` narration surface:
   non-combat `act()` callsites in Python that may not dispatch `mp_act_trigger_room`.
   Each site is gated by whether the matching ROM source uses `MOBtrigger = FALSE`
   around its `act()` emission. Track as ad-hoc follow-up commits (per the INV tracker
   note). Next unclosed site: unknown — run a grep for `act_to_room` vs `broadcast_room`
   calls in Python to identify candidates not yet wired to `mp_act_trigger_room`.
2. **Group/follower chain** (`src/act_move.c` follow-leader loop, `src/handler.c` group
   management): probe whether Python correctly propagates `ch->leader`/`ch->next_in_group`
   semantics on death, quit, and group leave. File as INV-041 if root cause spans modules.
3. **Mob-script trigger coverage** (`src/mob_prog.c` TRIG_* dispatch): probe remaining
   trigger types not yet wired in `mud/mobprog.py` (TRIG_RANDOM, TRIG_GREET, TRIG_ALL,
   TRIG_ENTRY vs current coverage).
