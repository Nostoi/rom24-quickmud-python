# Session Summary — 2026-06-12 — FIGHT-059: injury-feedback messages missing from apply_damage

## Scope

Continuation from v2.14.5 (INV-044 closed). The session executed the three cross-file
invariant probe candidates listed in the previous handoff — position-transition broadcast,
`stop_fighting` both=False call sites, and `check_killer` cross-file coherence — using the
probe-then-scope method (read ROM C contract → read Python equivalent → write one failing
test if divergence found).

Two probes were clean; one produced a real divergence (FIGHT-059).

## Probe Results

| Candidate | ROM C reference | Python equivalent | Verdict |
|-----------|----------------|-------------------|---------|
| Position-transition broadcast (STUNNED/MORTAL/INCAP/DEAD) | `src/fight.c:836-869` (`switch(victim->position)` in `damage()`) | `mud/combat/engine.py:apply_position_change` | ✅ CLEAN (four critical states handled); ❌ DIVERGENCE found in `default:` case → filed as FIGHT-059 |
| `stop_fighting` both=False call sites | `src/fight.c:1438-1453` and `src/fight.c:82` | `mud/combat/engine.py:stop_fighting`, `mud/game_loop.py:1607` | ✅ CLEAN — Python walks `character_registry`, clears victim + (if both=True) all fighters, calls `update_pos` — exact ROM match; call site `both=False` at `game_loop.py:1607` mirrors ROM `violence_update:82` |
| `check_killer` cross-file coherence | `src/fight.c:1226-1287` | `mud/combat/engine.py:check_killer` | ✅ CLEAN — masterless-charm path appears to call `stop_follower` when ROM returns early, but `stop_follower` guards `master is None` at line 53 and returns immediately — functionally equivalent |

## Outcomes

### `FIGHT-059` — ✅ FIXED

- **Python**: `mud/combat/engine.py:apply_damage` (after `apply_position_change`)
- **ROM C**: `src/fight.c:864-869`
- **Divergence**: ROM `damage()` has a `switch(victim->position)` with a `default:` case that
  fires when the victim's position stays at a non-critical state (FIGHTING/STANDING/RESTING/
  SLEEPING) after a hit. It delivers two optional messages to the victim: `"{RThat really did
  HURT!{x"` when `dam > victim->max_hit / 4`, and `"{RYou sure are BLEEDING!{x"` when
  `victim->hit < victim->max_hit / 4`. Python had no equivalent — victims received zero
  injury-feedback for non-critical hits.
- **Fix**: Added the two-condition block in `apply_damage` after `apply_position_change`,
  guarded by `victim.position > Position.STUNNED` (exact equivalent of the ROM `default:`
  case condition). Uses `//` (correct for provably non-negative operands, bit-for-bit
  identical to C `/`).
- **Collateral fix**: `test_attack_damages_but_not_kill` asserted `victim.messages[-1]` to be
  the hit-verb DEVASTATE line, but now HURT appends after it (ROM-correct ordering). Updated
  the assertion to `any()` membership check.
- **Tests**: `tests/test_combat.py::test_apply_damage_hurt_and_bleeding_messages` (4 cases:
  HURT-only on big hit, BLEEDING-only on low HP, both on big-hit + low HP, negative guard
  for STUNNED position — verifies HURT/BLEEDING do NOT fire when victim knocked down).
  Verified red before fix, green after. Full suite 5609/5609.

## Files Modified

- `mud/combat/engine.py` — added 7-line HURT/BLEEDING block inside `apply_damage` after
  `apply_position_change` (mirroring ROM `fight.c:864-869`)
- `tests/test_combat.py` — new test `test_apply_damage_hurt_and_bleeding_messages` (4 cases);
  fixed `test_attack_damages_but_not_kill` assertion (`[-1]` → `any()`)
- `docs/parity/FIGHT_C_AUDIT.md` — added FIGHT-059 row (✅ FIXED 2.14.6)
- `CHANGELOG.md` — added `[2.14.6]` Fixed entry
- `pyproject.toml` — 2.14.5 → 2.14.6

## Test Status

- `pytest tests/test_combat.py::test_apply_damage_hurt_and_bleeding_messages -n0` — 1/1 passing
- Full suite: **5609/5609 passing, 4 skipped** (run 2026-06-12, post-fix)

## Next Steps

All three probe candidates from the previous handoff have been verified. FIGHT-059 is closed.
The cross-file invariants pass continues. Suggested next probe areas:

1. **`check_assist` charm-loop safety** — ROM `src/fight.c:112-170` `check_assist` iterates
   `char_list`; Python `mud/combat/assist.py:check_assist` iterates `character_registry`.
   Verify that the charm-follow chain traversal (`fch->master == ch->fighting` guard at
   ROM `:138-144`) matches Python's equivalent, especially for mobs with ACT_ASSIST.
2. **`violence_update` stopping rule** — ROM `src/fight.c:76-82` stops fighting when
   `ch->in_room != victim->in_room` (different rooms) by calling `stop_fighting(ch, FALSE)`.
   Verify Python `game_loop.py:violence_tick` handles the room-mismatch case with the
   correct `both=False` flag and no extra side effects.
3. **`gain_exp` level-cap guard** — ROM `src/fight.c:919-924` clamps XP gain so a kill
   can't push a character past `level+1`. Verify Python `mud/groups/xp.py:group_gain` or
   `mud/characters/experience.py:gain_exp` applies the equivalent cap.

For each: read ROM C contract → read Python equivalent → write one failing test if divergence
found → close as single-gap commit or file as INV-NNN.
