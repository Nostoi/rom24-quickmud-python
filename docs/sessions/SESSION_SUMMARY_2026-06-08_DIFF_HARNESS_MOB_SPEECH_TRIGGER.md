# Session Summary — 2026-06-08 — Diff-Harness: mob SPEECH trigger + __mob_prog meta-command (2.13.23)

## Scope

Picked up from the 2.13.22 handoff's "Next Steps — mob scripts (`mob_prog.c`)". Implemented the
`__mob_prog=<trig>:<phrase>:<code>` meta-command in both the C shim and Python replay — injecting
mob programs at scenario runtime without editing area files (hermetic scenarios). Built the
`mob_speech_trigger` static scenario: loads the Midgaard wizard, injects a SPEECH trigger, issues
`say hello`, and verifies both engines fire `mp_speech_trigger` identically. Also fixed a latent
normalization gap in `compare.py` where C golden `affect_flags` (lowercase) differed in case from
Python's IntFlag enum names (uppercase), which was invisible until a watched NPC with active affects
appeared in a scenario.

## Outcomes

### `__mob_prog=<trig>:<phrase>:<code>` meta-command — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c` (after `__mob_carry` handler)
- **Python replay**: `tools/diff_harness/pyreplay.py:_run_python_command`
- **ROM C reference**: `src/mob_prog.c:1191–1199` (`mp_act_trigger` speech dispatch),
  `src/merc.h:2124` (`HAS_TRIGGER` checks `pIndexData->mprog_flags`)
- **Design**: C side uses `alloc_perm(sizeof(MPROG_LIST))` + `SET_BIT(mprog_flags, trigger)`;
  `prg->code` is set directly (no vnum resolution needed — `program_flow` uses `prg->code`
  verbatim, `src/mob_prog.c:1196`). Python side appends a `MobProgram` to `mob.mob_programs`;
  `_get_programs` and `_has_mobprog_trigger` both check the instance-level list.
- **Trigger scope**: SPEECH trigger chosen as first target because it is keyword-matched
  (`strstr(argument, trig_phrase)`) — deterministic, no seed brackets needed. GREET/ENTRY/RANDOM
  are percent-gated (`number_percent() < atoi(trig_phrase)`) and would require `__seed` brackets.

### `mob_speech_trigger` static scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/mob_speech_trigger.json`
- **Design**: `start_room=3001`, `__seed=4321` (locks wizard wealth generation to match C),
  `__mload=3000` (Midgaard wizard), `__mob_prog=speech:hello:say Hello adventurer!`,
  `say hello` → both engines produce `"The wizard says 'Hello adventurer!'"`.
- **Oracle verified**: C and Python output identical on step 3 (`say hello`):
  `["{6You say '{7hello{6'{x", "{6The wizard says '{7Hello adventurer!{6'{x"]`
- **Golden**: `tests/data/golden/diff/mob_speech_trigger.golden.json` (5 steps)
- **Tests**: `test_python_matches_c_golden[mob_speech_trigger]` — PASSED; 9/9 smoke tests pass.

### `affect_flags` case normalization fix — ✅ FIXED

- **File**: `tools/diff_harness/compare.py:_normalize_char`
- **Root cause**: C oracle stores affect flag names as lowercase strings (`detect_invis`) from
  ROM's string tables; Python snapshots emit IntFlag enum names (`DETECT_INVIS`, uppercase).
  No prior scenario had a watched NPC with active affect flags, so the gap was invisible.
- **Fix**: `affect_flags=sorted(f.lower() for f in c.affect_flags)` — one-character change.
- **Tests**: `test_normalize_sorts_unordered_lists_and_strips_ansi` updated to assert
  lowercase `["a", "b"]`; all 38 diff-harness unit + generated tests pass.

## Files Modified

- `src/diff_shim/diffmain.c` — `__mob_prog=<trig>:<phrase>:<code>` C shim handler (44 lines)
- `tools/diff_harness/pyreplay.py` — `__mob_prog` Python meta-command handler (18 lines)
- `tools/diff_harness/compare.py` — `affect_flags` lowercase normalization in `_normalize_char`
- `tools/diff_harness/scenarios/mob_speech_trigger.json` — new static scenario (5 steps)
- `tests/data/golden/diff/mob_speech_trigger.golden.json` — new golden (C oracle, 5 steps)
- `tests/test_diff_harness_unit.py` — updated `affect_flags` assertion to expect lowercase
- `CHANGELOG.md` — added 2.13.23 section with three Added/Fixed entries
- `pyproject.toml` — 2.13.22 → 2.13.23

## Test Status

- **Diff harness golden**: 9/9 passing (`tests/test_differential_smoke.py`)
- **Diff harness generated**: 15/15 passing (`tests/test_diff_harness_generated.py`)
- **Diff harness unit**: 13/13 passing (`tests/test_diff_harness_unit.py`)
- **Full suite**: 5434 passed, 4 skipped, 0 failed
- `ruff check .` clean; `gitnexus_detect_changes` HIGH risk (expected — `diffmain.c:main` touched;
  all affected processes trace to C shim only, not the game engine)

## Next Steps

1. **Additional spells** (`detect_evil`, `fly`, `bless`) — extend the Hypothesis diff machine.
   Each spell needs: a `__learn=<spell_name>` step to give the caster the skill at 100%,
   a `__seed` bracket around the cast (the skill check uses `number_percent()`), and a
   Hypothesis rule following the `learn_and_cast_armor` pattern in `generated.py`. The
   `detect_evil` spell is the easiest first target (no duration RNG — just an affect apply).
2. **Shop transaction atomicity** (INV candidate) — probe insufficient-funds and item-not-for-sale
   error exit paths in `do_buy`/`do_sell` for atomicity divergences between C and Python.
   A scenario with a player who has exactly 0 silver buying a 300-silver item would isolate the
   error path cleanly.
3. **Cross-INV: affect-tick ordering** — verify that `char_update` processes affects in the same
   order as ROM C (`src/update.c:char_update`), specifically the `affect_remove` vs
   `affect_update` call ordering for multi-affect characters.
