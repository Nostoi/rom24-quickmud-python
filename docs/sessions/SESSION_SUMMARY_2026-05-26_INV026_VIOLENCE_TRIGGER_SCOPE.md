# Session Summary — 2026-05-26 — INV-026 violence-trigger dispatch scope (2.9.43)

## Scope

Resuming from 2.9.42 (INV-025 follow-up sweep landed; tests 2223/3 skipped).
Two pieces of work this session:

1. **`char.location` audit sweep** — follow-up probe surfaced by the
   `do_put` bug in the INV-025 sweep (chars have no `.location`
   attribute; `Affect.location` is the legit one). Grepped every
   `getattr(char, "location"...)` / `getattr(ch, "location"...)` /
   `getattr(occupant, "location"...)` site. Result: one more real-bug
   typo cluster fixed (`do_eat`/EAT-004 broadcast in
   `mud/commands/consumption.py:66` had the same fallback pattern as
   `do_put`); five dead-code fallback sites stripped.
2. **INV-026 — TRIG_FIGHT / TRIG_HPCNT dispatch scope.** Probe-then-
   scope on the next mob-trigger contract after INV-025's TRIG_ACT
   coverage. Found that Python fires both triggers from the end of
   `multi_hit` (the shallow HPCNT-001 enforcement point), so every
   `multi_hit` caller — assist, spec_funs, mob_cmds — wrongly
   provokes them. ROM fires only from `violence_update` after
   `multi_hit` returns, with a victim-still-fighting guard. Lifted
   the dispatch to `violence_tick` and filed INV-026.

GitNexus index refreshed at session start (was stale at `c75f898`,
now stale again at `6b21fa9` — three new commits postdate the
refresh).

## Outcomes

### `char.location` audit sweep — ✅ CLOSED (`476084d5`)

- **Python touched**:
  - `mud/commands/obj_manipulation.py` — `_perform_remove` + `do_quaff`
    (lines 362, 516)
  - `mud/commands/consumption.py` — `do_eat`/EAT-004 broadcast (line 66)
  - `mud/spawning/reset_handler.py` — three audit-tally `setattr` sites
    (lines 141, 148, 216, 222)
- **ROM C**: no specific ROM file — this is dead-code cleanup in the
  spirit of "Character has no `.location`; that's an `Affect`
  attribute, not `Character`. The fallback was a typo cluster from
  early test-fixture code."
- **Fix**: Stripped the `or getattr(char, "location", None)` /
  `or getattr(ch, "location", None)` fallbacks. `char.room` always
  wins in normal operation; the inner `getattr` never resolved.
  Removing the dead alternative prevents the typo cluster from
  spreading further.
- **Tests**: No new tests; verified by running the affected areas'
  integration suites (do_put, equipment, consumables, spawning,
  db_resets_rom_parity — 129/129 green) plus the full suite at the
  end of the session (4760 passed, 4 skipped).

### INV-026 VIOLENCE-TRIGGER-DISPATCH-SCOPE — ✅ ENFORCED (`c48224af`)

- **Python**:
  - `mud/game_loop.py:violence_tick` (lines 1322-1348) — now owns
    the dispatch. After `multi_hit(ch, victim, dt=None)` returns,
    fires `mobprog.mp_fight_trigger(ch, victim)` then
    `mobprog.mp_hprct_trigger(ch, victim)` only if
    `getattr(ch, "is_npc", False) and getattr(ch, "fighting", None) is victim`.
    The `attacker.fighting is victim` re-read (not the loop-local
    `victim` parameter) mirrors ROM's `(victim = ch->fighting) == NULL`
    re-fetch.
  - `mud/combat/engine.py:multi_hit` (line 360 area) — the previous
    shallow HPCNT-001 enforcement point — no longer dispatches.
- **ROM C**: `src/fight.c:60-99 violence_update` — the only ROM site
  that fires either trigger. Per-iteration sequence: `multi_hit` →
  `(victim = ch->fighting) == NULL` guard → `check_assist` →
  `IS_NPC(ch)` then HPCNT/FIGHT.
- **Pre-INV-026 symptom**: every assist-mob join, every spec_fun
  attack, and every `mob kill` directive dispatched TRIG_FIGHT and
  TRIG_HPCNT on the attacker, contradicting ROM. Plus the
  victim-killed-mid-round case fired triggers on a dead victim.
- **Adjacent misplacement deferred**: `mud/combat/engine.py:multi_hit`
  still embeds `check_assist(attacker, victim)` at line 317; ROM
  places it in `violence_update` after multi_hit returns
  (`src/fight.c:90`). Same misplacement pattern as INV-026 was. Filed
  in the tracker row but intentionally deferred to a separate
  gap-closer.
- **Test rewrites**:
  - `tests/integration/test_hpcnt_once_per_pulse.py::test_hpcnt_fires_exactly_once_per_multi_hit`
    renamed to `test_hpcnt_fires_exactly_once_per_violence_tick`; now
    drives `violence_tick(do_combat=True)` instead of `multi_hit`.
  - `tests/test_mobprog_triggers.py::test_event_hooks_fire_rom_triggers`
    drives `violence_tick(do_combat=True)` directly after `game_tick`
    (was relying on `multi_hit` to fire the triggers); sets
    `position=STANDING` + boosts hp before the violence pulse so the
    guard holds.
- **Tests**:
  `tests/integration/test_inv026_violence_trigger_dispatch.py` — 3/3
  (multi_hit-direct silence; violence_tick dispatch; victim-died guard).
  Full suite: 4760 passed, 4 skipped.

## Files Modified

- `mud/combat/engine.py` — removed `mp_fight_trigger` / `mp_hprct_trigger`
  dispatch from end of `multi_hit`
- `mud/game_loop.py` — added the dispatch to `violence_tick` after
  `multi_hit`, guarded by `attacker.fighting is victim`
- `mud/commands/obj_manipulation.py` — dead `char.location` fallback
  stripped from `_perform_remove` + `do_quaff`
- `mud/commands/consumption.py` — dead `char.location` fallback
  stripped from `do_eat`/EAT-004 broadcast
- `mud/spawning/reset_handler.py` — three audit-tally `setattr` sites
  cleaned up
- `tests/integration/test_inv026_violence_trigger_dispatch.py` — NEW
  (3 tests)
- `tests/integration/test_hpcnt_once_per_pulse.py` — `_multi_hit` test
  renamed + rewritten to `_violence_tick`
- `tests/test_mobprog_triggers.py` — `test_event_hooks_fire_rom_triggers`
  updated to drive `violence_tick` directly
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-026 row added
- `CHANGELOG.md` — 2.9.43 section
- `pyproject.toml` — 2.9.42 → 2.9.43

## Test Status

- New INV-026 sweep tests: 3/3 ✅
- HPCNT-001 tests (rewritten): 2/2 ✅
- `test_mobprog_triggers.py`: 6/6 ✅
- Full suite: **4760 passed, 4 skipped** in 664s wall-clock

## Next Steps

1. **Close the `check_assist` misplacement** as a follow-up
   gap-closer — ROM `src/fight.c:90` calls `check_assist` from
   `violence_update` after `multi_hit` returns, not inside
   `multi_hit`. Same shape as INV-026; intentionally split for
   commit hygiene. Will not need a new INV row (single-file move
   inside the existing combat module).
2. **GitNexus refresh** — index is stale at `6b21fa9`; refresh
   before the next probe so `gitnexus_impact` calls return accurate
   blast-radius numbers for the three new commits.
3. **Continue probe-then-scope at 23/~20 INV budget** (now over by
   three after INV-026 filed). Per AGENTS.md soft cap, candidates
   for future consolidation if budget needs to come back down:
   INV-016 / INV-019 (position-transition broadcast / silent
   promotion-on-heal), INV-006 / INV-009 (fighting-pointer
   coherence / registry-disconnect cleanup). INV-026 is its own
   contract — would not merge cleanly into any existing row.
