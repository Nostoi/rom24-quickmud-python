# Session Summary — 2026-05-30 — INV-031 PC Death Preserves Group + Probes

## Scope

Continued from `SESSION_SUMMARY_2026-05-30_INV030_BLESS_OBJECT_BRANCH.md`.

Cross-file invariants active session:
1. **INV-031 PC-DEATH-PRESERVES-GROUP** — fixed `raw_kill` to only call
   `die_follower` for NPC victims, matching ROM `extract_char(ch, IS_NPC(ch))`
   where `fPull=FALSE` for PCs preserves group/follower relationships.
2. Probed affect-tick interaction across modules (plague spread in char_update
   vs SINGLE-DELIVERY) — existing invariants cover the key contracts.
3. Probed `char_update` operation ordering divergence — filed as carried-open
   (minor impact, not INV-worthy yet).
4. Fixed `is_same_group` identity comparison bug (`==` → `is`).

## Outcome

### INV-031 PC-DEATH-PRESERVES-GROUP — ✅ FIXED (2.11.56)

**Root cause**: `mud/combat/death.py:raw_kill` called `die_follower(victim)`
unconditionally for both PCs and NPCs. ROM `raw_kill` calls
`extract_char(victim, IS_NPC(victim))` — `fPull=TRUE` for NPCs calls
`die_follower`, but `fPull=FALSE` for PCs does NOT.

**ROM verification** (src/fight.c:1694-1722, src/handler.c:2103-2187):
- `raw_kill` → `extract_char(victim, IS_NPC(victim))`
- `extract_char` line 2120-2122: `if (fPull) die_follower(ch);`
- NPC death (`fPull=TRUE`): `die_follower` called, group dissolved
- PC death (`fPull=FALSE`): `die_follower` NOT called, group preserved

**Fix**: Gate `die_follower(victim)` behind `is_npc` in `raw_kill`.
NPC path unchanged; PC path now preserves `leader`, `master`, and
all followers' pointers (matching ROM).

**Gameplay impact of the bug**:
- When a PC group leader died, the entire group dissolved in Python
  (all members' `leader` reset to self). In ROM, the group survives;
  members who return to the same room are still in the group.
- A dead PC following someone lost their `master` and `leader` pointers.
  In ROM, they'd still be following when they respawn.

### `is_same_group` identity fix

`mud/commands/group_commands.py:is_same_group` used `==` (dataclass
field equality) instead of `is` (identity). ROM uses pointer comparison.
Two different `Character` instances with identical fields would match
under `==` but not under `is`, silently producing wrong group results
if duplicate Character objects ever existed. Fixed to use `is`,
matching `mud/characters/__init__.py:is_same_group` and ROM
(`src/act_comm.c:2018-2028`).

### Probe: Affect-tick interaction (plague spread vs SINGLE-DELIVERY)

Read ROM `src/update.c:794-846` plague tick and Python
`mud/game_loop.py:560-651` `_char_update_tick_effects`. Key findings:

1. **SINGLE-DELIVERY** (INV-001): Plague tick messages use
   `_message_room` → `room.broadcast` (already verified single-delivery).
   ✅ Covered.
2. **TICK-ITERATION-SAFETY** (INV-017): `char_update` iterates
   `list(character_registry)` snapshot. ✅ Covered.
3. **ACT/TRIG_ACT formatting gap**: Plague tick uses hardcoded
   `_message_room(f"...")` instead of `act_format`, so no per-recipient
   PERS masking (INV-027) and no TRIG_ACT dispatch (INV-025 follow-up
   sweep). Not a new invariant — it's part of the existing
   INV-025 follow-up sweep and the `act_format` coverage expansion.
4. **No new invariant needed** — existing INVs cover the key contracts.

### Probe: char_update operation ordering

ROM `char_update` order: regen → update_pos → **light decay → timer →
conditions** → affect ticks → damage effects.

Python `char_update` order: regen → update_pos → affect ticks → damage
effects → **light decay → timer → conditions**.

The divergence: ROM processes PC light decay, idle timer, and condition
decay BEFORE affect ticks and damage effects. Python processes them AFTER.

Most impactful scenario: a PC with a burning light about to go out AND
plague damage that kills them — ROM ticks the light down first, then the
PC may die; Python kills the PC first (light moves to corpse), then
light decay finds nothing to decay. Minor gameplay impact (one tick of
light duration).

Carried as open: not filing an INV row yet due to minor impact.

## Files Modified

- `mud/combat/death.py` — `raw_kill`: `die_follower(victim)` now gated
  behind `is_npc` (ROM `extract_char(ch, fPull)` semantics)
- `mud/commands/group_commands.py` — `is_same_group`: `==` → `is`
  (ROM pointer comparison)
- `tests/integration/test_inv031_pc_death_preserves_group.py` — new (4 tests)
- `tests/integration/test_inv020_group_leader_coherence_on_raw_kill.py` —
  docstring updated (NPC-only scope, cross-ref INV-031)
- `tests/integration/test_group_combat.py` — test_group_disbands_when_leader_dies
  updated to match ROM (PC group survives leader death)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-031 row added,
  INV-020 description updated (NPC-only `die_follower` scope)
- `CHANGELOG.md` — 2.11.56 entry
- `pyproject.toml` — 2.11.55 → 2.11.56

## Verification

- `pytest tests/integration/test_inv031_pc_death_preserves_group.py -n0 -v` — 4 passed
- `pytest tests/integration/test_inv020_group_leader_coherence_on_raw_kill.py tests/integration/test_inv020_extract_quit_cleanup.py tests/integration/test_pc_death_keeps_connection.py -n0 -v` — 7 passed
- `pytest -n auto -q` — 5091 passed, 4 skipped
- `ruff check mud/commands/group_commands.py` — all checks passed
- `ruff format mud/commands/group_commands.py tests/integration/test_inv031_pc_death_preserves_group.py` — formatted

## Outstanding

- Continue cross-file invariant probe/close cycle.
- char_update operation ordering divergence (light decay / timer /
  conditions BEFORE vs AFTER affect ticks) — minor impact, carried open.
- `Character.pet` type annotation hygiene — future type pass.
- `curse` handler type annotation hygiene — future type pass.
- INV-025 follow-up sweep: plague tick messages should dispatch TRIG_ACT
  and use PERS masking (part of existing sweep, not new INV).
- INV-027 coverage expansion: plague tick `_message_room` callers bypass
  `act_format`, no per-recipient PERS masking (existing INV scope).