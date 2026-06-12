# Session Summary — 2026-06-12 — FIGHT-060: check_assist elif chain skips ASSIST_ALIGN/ASSIST_VNUM

## Scope

Continuation from v2.14.6 (FIGHT-059 closed). The session ran the three cross-file invariant
probe candidates listed in the previous handoff — `check_assist` charm-loop safety,
`violence_update` room-mismatch stopping rule, and `gain_exp` level-cap guard — using the
probe-then-scope method (read ROM C contract → read Python equivalent → write one failing test
if divergence found).

One probe produced a real divergence (FIGHT-060); two were clean.

## Probe Results

| Candidate | ROM C reference | Python equivalent | Verdict |
|-----------|----------------|-------------------|---------|
| `check_assist` NPC assist flag OR chain | `src/fight.c:139-178` | `mud/combat/assist.py:check_assist` | ❌ DIVERGENCE — `elif` chain skips ASSIST_ALIGN/ASSIST_VNUM when ASSIST_RACE flag set but race doesn't match → filed+closed as FIGHT-060 |
| `violence_update` room-mismatch stopping rule | `src/fight.c:76-82` | `mud/game_loop.py:violence_tick:1607` | ✅ CLEAN — `stop_fighting(ch, both=False)` called when rooms differ; room comparison uses `==` (correct for `eq=False` Room dataclass) |
| `gain_exp` level-cap guard | `src/update.c:120-142` | `mud/advancement.py:gain_exp` | ✅ CLEAN — ROM has no "can't skip past level+1" guard; `while` loop in both C and Python allows multi-level gains. Session note mis-cited `fight.c:919-924` (that range is the death trigger); real XP logic is in `update.c:127-139`. Python floor (`max(exp_per_level, ch.exp + gain)`) matches ROM `UMAX` correctly. |

## Outcomes

### `FIGHT-060` — ✅ FIXED

- **Python**: `mud/combat/assist.py:check_assist` (NPC assist block, lines ~99-123)
- **ROM C**: `src/fight.c:139-150`
- **Divergence**: ROM `check_assist` evaluates all five NPC assist conditions as a single flat
  `||` OR chain. Python used `elif` for the ASSIST_RACE / ASSIST_ALIGN / ASSIST_VNUM checks.
  When the ASSIST_RACE flag is set but the inner race predicate fails (different race), Python's
  `elif` branch is entered (flag is truthy), the body leaves `should_assist = False`, and
  subsequent `elif ASSIST_ALIGN` / `elif ASSIST_VNUM` branches are silently skipped. A mob with
  both ASSIST_RACE and ASSIST_ALIGN (different race, same alignment as attacker) would fail to
  assist in Python while ROM would correctly trigger the assist. This is also an MM RNG desync:
  the `number_bits(1)` skip draw and target-selection `number_range` loop are gated on
  `should_assist`, so a missed assist means fewer RNG draws, desyncing downstream combat events
  (same class as FIGHT-053).
- **Fix**: Converted `elif rch_off_flags & OffFlag.ASSIST_RACE/ALIGN/VNUM` to independent `if`
  checks — 3-character change per line (`elif` → `if`). Added a comment citing ROM C and
  explaining the || vs elif semantics divergence. The separate group-membership `if` at the end
  was already correct (ROM's flag-less cond2 handled independently).
- **Tests**: `tests/integration/test_fight060_check_assist_elif_chain.py` (2 cases):
  - `test_fight060_assist_align_fires_when_race_flag_set_but_race_differs` — assister has
    ASSIST_RACE|ASSIST_ALIGN, different race, same alignment; asserts `multi_hit` fires.
  - `test_fight060_assist_vnum_fires_when_race_flag_set_but_race_differs` — assister has
    ASSIST_RACE|ASSIST_VNUM, different race, same vnum; asserts `multi_hit` fires.
  Both patched `number_bits → 1` (bypass 50% skip guard), `can_see_character → True`,
  `is_safe → False`, and `number_range → 0` (deterministic target selection), following the
  precedent of FIGHT-053's test. Both verified red before fix, green after.

## Files Modified

- `mud/combat/assist.py` — converted 3 `elif` to `if` in the NPC assist block; added ROM
  citation comment (mirroring `src/fight.c:141-150`)
- `tests/integration/test_fight060_check_assist_elif_chain.py` — new integration test (2 cases)
- `docs/parity/FIGHT_C_AUDIT.md` — added FIGHT-060 row (✅ FIXED 2.14.7)
- `CHANGELOG.md` — added `[2.14.7]` Fixed entry
- `pyproject.toml` — 2.14.6 → 2.14.7

## Test Status

- `pytest tests/integration/test_fight060_check_assist_elif_chain.py -n0` — 2/2 passing
- `pytest tests/integration/test_fight053_check_assist_rng_increment.py` — 1/1 passing (no regression)
- Full suite: **5611/5611 passing, 4 skipped** (run 2026-06-12, post-fix)

## Next Steps

All three probe candidates from the previous handoff have been verified. FIGHT-060 is closed.
The cross-file invariants pass continues. Suggested next probe areas:

1. **`check_assist` ASSIST_PLAYERS level check** — ROM `src/fight.c:116-124` ASSIST_PLAYERS
   path: `rch->level + 6 > victim->level`. A mob with ASSIST_PLAYERS helps a player fighting
   a weaker mob when the mob's level + 6 exceeds the victim's level. Verify Python checks this
   comparison using the same operand order and direction (> not >=).
2. **`update_pos` missing cases** — ROM `src/fight.c:1404-1435` `update_pos` sets position
   based on HP thresholds (MORTAL < 0, INCAP < -5, etc.) and also handles transitions from
   RESTING/MEDITATING/SLEEPING. Verify Python `apply_position_change` covers all branches,
   particularly the RESTING→FIGHTING auto-stand case.
3. **`group_gain` party-size scaling** — ROM `src/fight.c:1736-1788` loops `in_room->people`
   for group members. Verify Python `mud/groups/xp.py:group_gain` uses `room.people` (not
   `character_registry`) and applies the correct `group_levels` divisor formula.
