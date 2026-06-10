# Session Summary — 2026-06-09 — Diff-harness C-oracle for TRIG_KILL and TRIG_DEATH

## Scope

Continuing from v2.13.57. The "Next Steps" from the SURR/FIGHT/HPCNT session listed TRIG_KILL and
TRIG_DEATH as the remaining Class 11 dispatch paths without C-oracle scenarios. Both require mob
death, which needs a deterministic instant-kill meta-command. This session added `__instant_kill`
to both the C shim and Python replay, captured C-oracle goldens for `mob_kill_trigger` and
`mob_death_trigger`, and resolved four parity bugs surfaced during the diff comparison.

## Outcomes

### `__instant_kill` meta-command — ✅ ADDED

- **C**: `src/diff_shim/diffmain.c` — new `strncmp(line, "__instant_kill", 14)` handler; calls
  `damage(ch, mob, mob->hit + 1, TYPE_HIT, DAM_BASH, TRUE)` on the first NPC in the room.
  Exercises the full ROM death path (TRIG_DEATH, `group_gain`, `raw_kill`, corpse).
- **Python**: `tools/diff_harness/pyreplay.py` — equivalent `apply_damage(char, mob, mob.hit+1,
  DamageType.BASH, dt=1000)` handler. `dt=1000` (TYPE_HIT) mirrors C's parry/dodge/shield check
  order.
- **ROM C ref**: `src/fight.c:damage()` — TYPE_HIT triggers all defensive checks before applying damage.

### `mob_kill_trigger` C-oracle scenario — ✅ ADDED + PASSING

- **Scenario**: `tools/diff_harness/scenarios/mob_kill_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_kill_trigger.golden.json` (7 steps, C binary)
- **ROM C refs**:
  - `src/fight.c:damage()` — TRIG_KILL fires when `victim->fighting == NULL` on the first hit
    (even a miss, `dam=0`). The `kill drunk` command triggers it immediately.
  - `src/mob_prog.c:mp_percent_trigger` — `trig_phrase=101` is unconditional (`number_percent()`
    returns 1-100, so `< 101` is always true).
- **Design**: mob 3064 (drunk, level 2) in room 3008, `__mob_prog=kill:101:say KILL trigger fired!`.
  PC does `kill drunk` → trigger fires on first hit regardless of hit/miss.
- **C oracle step 6 output**: `"The drunk says 'KILL trigger fired!'"` confirmed in step after `kill drunk`.
- **Tests**: `test_python_matches_c_golden[mob_kill_trigger]` — PASSED (no engine changes needed).

### `mob_death_trigger` C-oracle scenario — ✅ ADDED + PASSING (4 bugs fixed)

- **Scenario**: `tools/diff_harness/scenarios/mob_death_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_death_trigger.golden.json` (8 steps, C binary)
- **ROM C refs**:
  - `src/fight.c:918-922` — TRIG_DEATH fires after `group_gain` and before `raw_kill`, only when
    `HAS_TRIGGER(victim, TRIG_DEATH)`. Mob position temporarily set to STANDING during trigger.
  - `src/fight.c:death_cry` — `msg` initialized to `"You hear $n's death cry."` before
    `switch(number_bits(4))`; rolls 0-7 each map a specific gore message (cases 8-15 keep default).
- **Design**: mob 3064 in room 3008, `__mob_prog=death:101:say DEATH trigger fired!`.
  `__instant_kill` delivers the killing blow; `look` step verifies corpse + trigger message + death cry.
- **C oracle step 7 output**: `['You receive 42 experience points.', "The drunk says 'DEATH trigger fired!'", "You hear the drunk's death cry."]`
- **Tests**: `test_python_matches_c_golden[mob_death_trigger]` — PASSED after 4 bug fixes below.

### TRIG_DEATH ordering fix — ✅ FIXED

- **Python**: `mud/combat/engine.py:_handle_death`
- **ROM C**: `src/fight.c:918-922`
- **Bug**: TRIG_DEATH was firing inside `apply_damage` BEFORE `group_gain`/XP, inverting the RNG
  sequence vs C. `xp_compute`'s `number_range` came AFTER TRIG_DEATH's `number_percent` in Python,
  but BEFORE it in C.
- **Fix**: removed TRIG_DEATH call from `apply_damage`; added it in `_handle_death` after
  `group_gain`, guarded by `mob_has_trigger(victim, Trigger.DEATH)` (mirrors C's `HAS_TRIGGER` macro).
- **New symbol**: `mob_has_trigger(mob, trigger)` added to `mud/mobprog.py` — mirrors
  `HAS_TRIGGER` by checking `_get_programs(mob)` for any program with matching `trig_type & flag`.

### `death_cry` default message fix — ✅ FIXED

- **Python**: `mud/combat/death.py:death_cry`
- **ROM C**: `src/fight.c:1583-1606`
- **Bug**: `message_template` was initialized to `"$n hits the ground … DEAD."` (case 0's text).
  `number_bits(4)` rolls 8–15 have no matching case in the switch, so ROM preserves the
  pre-switch default `"You hear $n's death cry."`. Python's wrong initialization caused roll=15 to
  emit the case-0 message instead.
- **Fix**: initialize `message_template = "You hear $n's death cry."` and handle case 0 explicitly.
  Cases 2–7 also converted from a chained fallthrough loop to unconditional `elif` blocks (ROM's
  `break` is unconditional — missing parts use the default, not the next case). Only case 1 has a
  genuine C fallthrough (to case 2 when `material != 0`).

### `xp_compute` logon=0 bug fix — ✅ FIXED

- **Python**: `mud/groups/xp.py:xp_compute` line 257
- **ROM C**: `src/db.c:new_char` — always sets `ch->logon = current_time`
- **Bug**: `logon_time is not None` check treated `logon=0` (dataclass default for test chars)
  as Unix epoch. `elapsed = time.time() - 0 ≈ 1.75B seconds`, clamping `time_per_level` to 12
  instead of ROM's 10 for a fresh level-5 character. XP output: 52 (Python) vs 42 (C).
- **Fix**: changed to truthiness check `if logon_time`, matching `advancement.py:136` and
  `handler.py:762` which already use `if logon:`. `logon=0` → `elapsed=0` → `time_per_level=10`.

### Snapshot dead-char filter — ✅ FIXED

- **Python**: `tools/diff_harness/pysnap.py:snapshot_python`
- **Bug**: `chars_by_name` dict retained the dead mob after `raw_kill` set `mob.room = None`.
  The snapshot included the mob in the `chars` list; the C shim omits extracted chars.
- **Fix**: filter `chars_by_name.items()` to only include entries where `getattr(c, "room", None)
  is not None`.

## Files Modified

- `src/diff_shim/diffmain.c` — `__instant_kill` handler added
- `tools/diff_harness/pyreplay.py` — `__instant_kill` handler added
- `tools/diff_harness/scenarios/mob_kill_trigger.json` — new scenario (7 steps)
- `tools/diff_harness/scenarios/mob_death_trigger.json` — new scenario (8 steps)
- `tests/data/golden/diff/mob_kill_trigger.golden.json` — C-oracle golden
- `tests/data/golden/diff/mob_death_trigger.golden.json` — C-oracle golden
- `mud/combat/engine.py` — `_handle_death`: TRIG_DEATH moved after `group_gain`, guarded by `mob_has_trigger`
- `mud/combat/death.py` — `death_cry`: default message fixed, cases 2-7 converted to `elif` chain
- `mud/groups/xp.py` — `xp_compute`: logon=0 truthy check
- `mud/mobprog.py` — `mob_has_trigger()` helper added
- `tools/diff_harness/pysnap.py` — dead-char filter in `snapshot_python`
- `tests/test_mobprog_triggers.py` — `test_event_hooks_fire_rom_triggers`: victim now has TRIG_DEATH
  program so `mob_has_trigger` guard fires correctly
- `CHANGELOG.md` — added [2.13.58] entry
- `pyproject.toml` — 2.13.57 → 2.13.58

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — 36/36 passed
- `pytest tests/test_mobprog_triggers.py` — all passed (including fixed `test_event_hooks_fire_rom_triggers`)
- Full suite: **5,493 passed, 5 skipped** (run at 2.13.58 HEAD)

## Next Steps

Class 11 remaining work (in priority order):

1. **TRIG_RANDOM C-oracle scenario** — requires a seed sequence where `number_percent() < 100`
   fires on `mobile_update`. The trigger is unconditional for phrase "100" (always fires), but
   `mobile_update`'s random tick runs on a 1-in-8 chance, so RNG must be aligned. Probe with
   `__tick` and a known seed to find a seed where RANDOM fires.
2. **TRIG_DELAY C-oracle scenario** — fires when `mob->mprog_delay` reaches 0 in `mobile_update`.
   Requires a mob with `mprog_delay` > 0 at scenario start; `__tick` counts down and fires.
   Should be straightforward with the existing `__tick` meta-command.
3. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the next
   unverified surface outside Class 11. Candidates: async message delivery ordering, affect-tick
   edge contracts, position-transition invariants.
4. **Latent parity gap: wizard shop status** — pre-existing; Python's `_has_shop` returns False
   for mob 3000 (wizard) because the midgaard JSON area file has no `shops` section.
