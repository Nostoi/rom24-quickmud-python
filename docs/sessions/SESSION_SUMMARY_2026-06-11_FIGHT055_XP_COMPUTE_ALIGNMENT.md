# Session Summary — 2026-06-11 — FIGHT-055 xp_compute alignment gaps

## Scope

Continuation from v2.14.0 (FIGHT-054 closed). Active pass: cross-file invariants.
Session picked up from SESSION_STATUS.md which listed three probes under INV-044:
`do_rescue` stop-fighting argument, `violence_update` position guard, and
`check_assist` ASSIST_ALL vs group-assist ordering. All three probes were clean.
During investigation a new divergence was found in `mud/groups/xp.py:xp_compute`
vs `src/fight.c:1878-1914` (FIGHT-055, two sub-gaps).

## Outcomes

### `check_assist` ASSIST_ALL vs group-assist ordering — ✅ NO GAP

- **ROM C**: `src/fight.c:137-153` — single `if (off_flags & ASSIST_ALL || ...|| group_match)` OR chain
- **Python**: `mud/combat/assist.py:check_assist` — `if/elif` for each flag + separate `if ch_group`
- **Finding**: The structural difference (`elif` chains vs `||`) produces identical behavior — all
  branches set `should_assist = True`. The separate `if ch_group` block after the elif chain is
  additive, not exclusive — a character with BOTH ASSIST_ALL and a group match still reaches
  `should_assist = True` (via ASSIST_ALL first). No behavioral divergence.

### `do_rescue` stop-fighting argument — ✅ NO GAP

- **ROM C**: `src/fight.c:3094-3095` — `stop_fighting(ch, FALSE)` and `stop_fighting(victim, FALSE)`
  (not TRUE; the victim's opponents are NOT also stopped)
- **Python**: `mud/skills/handlers.py:rescue` (line ~7230) → `stop_fighting(foe, False)` +
  `stop_fighting(target, False)`
- **Finding**: Python correctly passes `False` for both calls. No divergence.

### `violence_update` position guard — ✅ NO GAP

- **ROM C**: `src/fight.c:66-102` — outer `IS_AWAKE(ch)` guard (position > POS_SLEEPING); inner
  guard at `src/fight.c:195-210` inside `multi_hit`: `if (ch->position < POS_RESTING) return;`
- **Python**: `mud/game_loop.py:violence_tick` — outer guard `position > Position.SLEEPING` before
  calling `multi_hit`; `mud/combat/engine.py:multi_hit` line ~322 `if attacker.position < Position.RESTING: return`
- **Finding**: Both the outer sleep guard and the inner stun guard are present and correct. No divergence.

### FIGHT-055 `xp_compute` alignment mutation + multiplier snapshot — ✅ FIXED (2.14.1)

- **Python**: `mud/groups/xp.py:xp_compute`
- **ROM C**: `src/fight.c:1878-1914`
- **Sub-gap A — zero base_exp skips alignment mutation**: Python lines 169-170 had
  `if base_exp <= 0: return 0`, exiting before the alignment block. ROM has no such early return.
  When `level_range < -9` gives `base_exp == 0`, ROM still runs the alignment block and
  `UMAX(1, change)` forces `change = 1` when `align_delta > 500` or `align_delta < -500`,
  so even a trivially weak kill nudges alignment by 1. Python left alignment unchanged.
- **Sub-gap B — XP multiplier reads pre-mutation alignment snapshot**: Python captured
  `gch_alignment = _resolve_level(getattr(gch, "alignment", 0))` before the alignment block
  (line 173) and used this snapshot in the XP multiplier conditions. ROM `fight.c:1916`
  reads `gch->alignment` post-mutation. A character whose alignment crosses a threshold during
  mutation (e.g. 510→426 crossing the 500 boundary) got the wrong XP rate: Python's
  "goodie two shoes" path (`gch_alignment=510>500`) gave `xp=base_exp/4`; ROM's "a little good"
  path (`gch->alignment=426>200`) gives `xp=base_exp/2`.
- **Fix**: (A) Removed `if base_exp <= 0: return 0` — alignment block now runs unconditionally,
  XP naturally computes to 0 when `base_exp==0`. (B) Added `post_alignment = gch.alignment`
  after the alignment block; replaced all four `gch_alignment` references in the multiplier
  (`elif gch_alignment > 500`, `elif gch_alignment < -500`, `elif gch_alignment > 200`,
  `elif gch_alignment < -200`) with `post_alignment`.
- **Collateral fix**: `tests/test_skills.py:test_skill_use_advances_learned_percent` was broken
  by sub-gap A removal because `xp_compute` now calls `number_range(0, 0)` for zero-base-exp
  kills (the real function short-circuits for `(0,0)` without consuming RNG state, but the test's
  monkeypatch lambda always calls `next(iter)`). Added `0` to `range_rolls` iterator.
- **Impact analysis**: `xp_compute` — HIGH risk label, 1 direct caller (`group_gain`), LOW
  actual blast radius.
- **Tests**: `tests/integration/test_fight055_xp_compute_alignment_gaps.py` — **2/2 passing**
  - `test_fight055_zero_base_exp_alignment_mutates` — verifies `gch.alignment` shifts from
    -600 to -601 when `base_exp==0` and `align_delta > 500`; verifies `xp_compute` returns 0.
  - `test_fight055_xp_multiplier_uses_post_mutation_alignment` — gch alignment 510→426
    crossing 500 boundary; verifies `awarded == 4` (post-mutation "a little good" path) not
    2 (snapshot "goodie" path). Both tests verified red before fix, green after.

## Files Modified

- `mud/groups/xp.py` — FIGHT-055: removed early `if base_exp <= 0: return 0`; added
  `post_alignment = gch.alignment` after alignment block; replaced `gch_alignment` with
  `post_alignment` in four XP multiplier branch conditions
- `tests/integration/test_fight055_xp_compute_alignment_gaps.py` — new file, 2 tests
- `tests/test_skills.py` — updated `range_rolls` iter in `test_skill_use_advances_learned_percent`
  (+1 element: `0` for `xp_compute nr(0,0)` call path)
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-055 filed and flipped ✅ FIXED (2.14.1)
- `CHANGELOG.md` — `[2.14.1]` Fixed entry for FIGHT-055
- `pyproject.toml` — 2.14.0 → 2.14.1

## Test Status

- `pytest tests/integration/test_fight055_xp_compute_alignment_gaps.py -v` — **2/2 passing**
- Related suite: `pytest tests/integration/test_xp_compute_level_zero_pc.py tests/integration/test_group_xp_npc_level_floor.py tests/integration/test_group_gain_tick_delivery.py tests/test_advancement.py` — **71/71 passing**
- Full suite: **5597/5601 passing, 4 skipped** (run 2026-06-11)

## Next Steps

Cross-file invariants pass continues. Next free INV ID: **INV-044** (still free).

The three probes from SESSION_STATUS.md are now exhausted (check_assist ordering — no gap;
do_rescue stop-fighting args — no gap; violence_update position guard — no gap).
FIGHT-055 filed and closed. Suggested next probes:

1. **`group_gain` NPC-level-contribution floor** — ROM `src/fight.c:1751`
   `total_levels += gch->level / 2` for NPCs (integer division; a level-1 NPC contributes 0).
   Verify Python `mud/groups/xp.py:group_gain` uses the same floor (currently uses `level // 2`
   which matches for non-negative, but confirm it handles the `total_levels <= 0` fallback).

2. **`apply_damage` damage-type logging** — ROM `src/fight.c:505-560` logs kills differently
   for NPC vs PC, and logs "is DEAD!!" to room. Verify Python `mud/combat/engine.py:apply_damage`
   death-message broadcast matches ROM.

3. **`damage` `dam_type` WEAPON_NONE path** — ROM `src/fight.c:375` — when `dam_type == WEAPON_NONE`
   and `dam == 0`, ROM still calls `update_pos`. Verify Python `apply_damage` handles this edge
   case for zero-damage weapon hits.
