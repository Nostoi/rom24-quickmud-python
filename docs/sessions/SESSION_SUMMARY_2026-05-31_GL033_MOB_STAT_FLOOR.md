# Session Summary — 2026-05-31 — GL-033 mob stat floor

## Scope

Picked up from `SESSION_STATUS.md`, which listed **GL-033** as the only open
correctness gap after GL-032. Closed it with the standard gap-closer TDD flow:
ROM C source read, GitNexus impact checked, failing NPC floor tests added first,
implementation changed, combat-parity expectations re-derived against ROM.

## Outcome

### `GL-033` — ✅ FIXED (2.12.12)

- **ROM C**: `src/handler.c:868-874` (`get_curr_stat`) returns
  `URANGE(3, ch->perm_stat[stat] + ch->mod_stat[stat], max)`. The same function
  handles PCs and NPCs; NPCs use `max = 25`.
- **Python**: `mud/spawning/templates.py` — `MobInstance.get_curr_stat` now
  clamps to `max(3, min(25, perm_stat + mod_stat))`, matching ROM's NPC floor.
- **Why it mattered**: after GL-032 added NPC `mod_stat`, negative stat affects
  could drive a mob's effective stat below 3. Directly-constructed zero-stat
  combat fixtures also fed wrong NPC STR/DEX values into bash/disarm/dirt-kick
  chance formulas.
- **Combat expectations re-derived**:
  - bash larger-victim chance: `50 + 20 + 3 - ((3 * 4) / 3)` = 69.
  - NPC zero-skill bash chance: `100 + 3 - ((3 * 4) / 3)` = 99.
  - disarm DEX-vs-STR term: `3 - 2 * 3`.
  - inside-terrain dirt-kick chance: `50 + 3 - (2 * 3) - 20` = 27.

## Files Modified

- `mud/spawning/templates.py` — NPC stat floor changed from 0 to 3.
- `tests/integration/test_get_curr_stat_floor_three.py` — added NPC floor
  regression cases, verified red-first.
- `tests/test_skill_combat_rom_parity.py` — re-derived expectations that had
  depended on old zero-floor NPC fixtures.
- `docs/parity/UPDATE_C_AUDIT.md` — GL-033 flipped to ✅ FIXED.
- `CHANGELOG.md` — added GL-033 entry under `[Unreleased]`.
- `pyproject.toml` — 2.12.11 → 2.12.12.

## Verification

- `pytest -n0 tests/integration/test_get_curr_stat_floor_three.py -q` —
  23 passed.
- `pytest -n0 tests/test_skill_combat_rom_parity.py -q` — 104 passed.

## Next Steps

Per-file audit tracker remains exhausted and GL-033 is closed. Resume the
cross-file-invariants probe pass; remaining candidates from the prior status are
position transitions, group/follower chain, and the broader INV-025 sweep
(non-combat `_push_message`/`broadcast_room` narration where the matching ROM
site uses `act()`).
