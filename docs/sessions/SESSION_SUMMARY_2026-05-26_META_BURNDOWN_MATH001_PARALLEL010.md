# Session Summary — 2026-05-26 — META burn-down MATH-001 + PARALLEL-010 (2.9.53–2.9.54)

## Scope

Continuation of the 2026-05-26 series. After the META audit landing
(2.9.52, Classes 1/7/8 in parallel sub-agents), burned down the two
concrete ❌ rows extracted from the audits in smallest-first order.

## Outcomes

### `MATH-001` — ✅ FIXED (`5d5e246`, 2.9.53)

- **Python**: `mud/combat/engine.py:1290` (`calculate_weapon_damage`)
- **ROM C**: `src/fight.c` `one_hit` —
  `dam += GET_DAMROLL(ch) * UMIN(100, skill) / 100;`
- **Gap**: Python used `// 100` (floor toward negative infinity); ROM
  uses C `/` (truncate toward zero). With cursed gear / debuffs
  `get_damroll(attacker)` can be negative, so the product can be
  negative, and any product not evenly divisible by 100 falls on the
  diverging side. Example: damroll=-1, skill=99 → product -99 →
  Python `-99 // 100 == -1` vs ROM `c_div(-99, 100) == 0`.
- **Fix**: `// 100` → `c_div(..., 100)`.
- **Test**: `tests/integration/test_weapon_damage_damroll_c_div.py`
  — 1/1 `test_damroll_uses_c_truncation_not_python_floor`.
- **Verification**: 29/29 targeted (test_weapon_damage + test_combat_death
  + integration test_weapon_damage_damroll_c_div). Pre-existing flake
  `test_auto_flags_trigger_and_wiznet_logs` is order-dependent
  (fails after `tests/integration/` regardless of MATH-001 fix
  state — verified by stashing the fix and rerunning the same
  combination).

### `PARALLEL-010` — ✅ FIXED (`90aa8ce`, 2.9.54)

- **Python**: `mud/commands/combat.py:683-688` (and line 665) — `do_flee`
- **ROM C**: `src/fight.c:2970-3028` `do_flee`
- **Gap**: Pre-fix wrote to `room.characters` / `new_room.characters`
  — neither attribute exists (Room defines `people`).
  `hasattr(room, "characters")` gate silently hid the source-room
  remove; `new_room.characters.append(char)` raised `AttributeError`
  caught by broad `try/except` that surfaced misleading "Flee failed"
  while `char.move` was still decremented. Net effect: character paid
  the move cost but didn't actually move — `char.room` was reassigned
  but `room.people` was never updated.
- **Fix**: replaced with canonical `room.remove_character(char)` /
  `new_room.add_character(char)` helpers (`mud/models/room.py:140, 157`).
  Also fixed the same parallel-rep bug at line 665 (room-broadcast
  loop iterated `room.characters` — silently empty; now iterates
  `room.people`). Added `isinstance(to_room, Room | int)` typecheck
  before `room_registry.get(to_room)` since some test setups pass a
  Room object directly while production exits store vnums (handled
  both forms).
- **Test**: `tests/integration/test_flee_moves_character.py` — 1/1
  `test_flee_moves_character_to_new_room`.
- **Verification**: 45/45 flee-adjacent
  (test_flee_moves_character + test_player_npc_interaction +
  test_state_transitions + test_mob_cmds_flee).

### Pre-existing flake discovered (NOT addressed)

`tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
fails when run after `tests/integration/` on master regardless of
MATH-001 or PARALLEL-010 fix state. Order-dependent / shared-state
issue with the immortal `messages` registry — the wiznet
"got toasted by Attacker" message isn't reaching the immortal's
mailbox when integration tests have run first. Verified by stashing
both fixes and rerunning — failure reproduces. Per standing rule,
filed for a future separate gap-closer; not silenced.

## Files Modified

### 2.9.53 (MATH-001)
- `mud/combat/engine.py:1290` — `// 100` → `c_div(..., 100)`
- `tests/integration/test_weapon_damage_damroll_c_div.py` — NEW
- `docs/parity/audits/MATH_AND_RNG.md` — MATH-001 row → ✅ FIXED
- `CHANGELOG.md` — 2.9.53 section
- `pyproject.toml` — 2.9.52 → 2.9.53

### 2.9.54 (PARALLEL-010)
- `mud/commands/combat.py:660-700` — canonical `room.remove_character` /
  `room.add_character`; fixed adjacent `room.characters` read at line 665
- `tests/integration/test_flee_moves_character.py` — NEW
- `docs/parity/audits/PARALLEL_REPRESENTATIONS.md` — PARALLEL-010 row → ✅ FIXED
- `CHANGELOG.md` — 2.9.54 section
- `pyproject.toml` — 2.9.53 → 2.9.54

## Test Status

- `tests/integration/test_weapon_damage_damroll_c_div.py` — 1/1 ✅
- `tests/integration/test_flee_moves_character.py` — 1/1 ✅
- Flee-adjacent (45 tests across 4 files) — all green
- Weapon-damage-adjacent (6 tests) — all green
- Full integration suite not re-run for either commit
  (low-blast-radius single-line fixes; targeted suites green)
- Known pre-existing flake (not regression):
  `test_auto_flags_trigger_and_wiznet_logs` when run after
  integration suite

## Next Steps

1. **Push approval** required for 2.9.53 and 2.9.54 (`5d5e246`,
   `90aa8ce`). Per standing rule, no push without explicit
   per-cluster approval ("yes push v2.9.54 to origin/master" or
   similar).
2. **BCAST-001 … BCAST-039 walk** (Class 1 burn-down). Verify
   helper-transitivity for each row first — many ❌ MISSING rows
   from the shallow audit will collapse to ✅ once helper coverage is
   confirmed (door commands via `world/movement.py`, combat skills
   via `damage()`).
   - **Top 3 ranked by agent**: `do_disarm`/`do_trip`/`do_dirt`/
     `do_surrender` (TO_VICT+TO_NOTVICT hit-feedback);
     `do_goto`/`@goto` (poofin/poofout);
     `do_invis`/`do_incognito` (visibility-transition broadcasts).
3. **Drift-risk cleanup batch** (8 PARALLEL ⚠️ rows + 3 MATH ⚠️
   rows): single mechanical-cleanup commit cycle. Inline hex flag
   aliases in `misc_player.py` / `player_config.py` /
   `remaining_rom.py` / `obj_manipulation.py` / `imm_load.py` +
   dead `.carrying` fallback in `consumption.py:308-316` + stale
   docstring at `handler.py:694`.
4. **Pre-existing flake** at
   `test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   — file as INV row or single gap-closer once isolated. Probable
   root cause: integration tests leave state in `character_registry`
   that breaks wiznet broadcast resolution in the death test's
   immortal mailbox.
5. **GitNexus refresh** — index still stale (last indexed `069f17f`,
   now 6 commits behind master). Run
   `npx gitnexus analyze --skip-agents-md` before any new probe.
6. **Remaining META classes** (when ready to audit more): Class 2
   ARITHMETIC_BOUNDARY (half-session), Class 3 GATE_CONSISTENCY
   (session), Class 4 TRIGGER_CALL_SITE_MIGRATION (half-session),
   Class 5 LIFECYCLE_STAGING (session+).
