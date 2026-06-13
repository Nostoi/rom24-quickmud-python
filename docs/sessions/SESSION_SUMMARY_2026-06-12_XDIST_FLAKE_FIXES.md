# Session Summary — 2026-06-12 — xdist flake fixes (test-isolation hardening)

## Scope

Continuation of the cross-file-invariants pass. The per-file audit tracker is
exhausted (only deferred track-only DB2 rows remain), and the two known xdist
flakes were the highest-value outstanding items in `SESSION_STATUS.md`. Both were
diagnosed to root cause and fixed. **Neither is a production parity bug** — both
are test-isolation defects (a test reading shared global state it didn't isolate,
and a test pinning the wrong RNG primitive).

---

## Outcomes

### `test_hpcnt_fires_exactly_once_per_violence_tick` — ✅ FIXED (2.14.23)

- **Test**: `tests/integration/test_hpcnt_once_per_pulse.py`
- **Root cause**: `violence_tick` walks the **global** `character_registry`
  (`mud/game_loop.py:1590`, `for ch in list(reversed(character_registry))`). The
  integration conftest seeds RNG but does **not** isolate `character_registry`.
  A fighting NPC leaked by a sibling test on the same xdist worker fired its own
  `mp_hprct_trigger`, inflating `len(calls)` past the asserted 1.
- **Fix**: snapshot and replace the registry contents **in place**
  (`character_registry[:] = [attacker, victim]`) so the pulse sees only the
  test's two actors, restoring `character_registry[:] = saved_registry` in the
  `finally`. In-place mutation (not rebind) matters — `violence_tick` holds the
  list by reference via module import.

### `test_ac_clamping_for_negative_values` — ✅ FIXED (2.14.23)

- **Test**: `tests/test_combat_rom_parity.py`
- **Root cause**: ROM's to-hit roll is `number_bits(5)` (`src/fight.c:508`,
  `while ((diceroll = number_bits(5)) >= 20)`), **not** `number_percent`, and a
  natural `diceroll == 0` is an automatic miss regardless of hitroll/AC
  (`src/fight.c:510`, mirrored at `mud/combat/engine.py:598`). The test pinned
  `number_percent`, which has no effect on the d20 to-hit decision, so leaked
  global RNG state landed on `diceroll == 0` ~1/20 runs and flaked the
  `"miss" not in result` assertion under `-n auto`.
- **Fix**: pin `mud.utils.rng_mm.number_bits` to 19 (the auto-hit roll —
  `diceroll != 19` guard means 19 always hits) for a deterministic hit.
- **Diagnosis proof**: a standalone repro with `number_bits` pinned to 0 yields
  `"You miss Victim."`; pinned to 19 yields `"You scratch Victim."`.

## Files Modified

- `tests/integration/test_hpcnt_once_per_pulse.py` — registry isolation
- `tests/test_combat_rom_parity.py` — pin `number_bits` not `number_percent`
- `CHANGELOG.md` — `[2.14.23]` Fixed entries
- `pyproject.toml` — 2.14.22 → 2.14.23

## Test Status

- `pytest -n0 tests/integration/test_hpcnt_once_per_pulse.py` — 2/2 passing
- `pytest -n0 tests/test_combat_rom_parity.py` — 10/10; `-n auto` — 10/10
- Combat-area parallel sweep (`-k "hpcnt or violence or combat or fight"`) —
  244 passed, 1 skipped
- `ruff check` on changed files — clean

### `MOBCMD-019` — `mob remember <unresolved>` left a stale mprog_target — ✅ FIXED (2.14.24)

- **Python**: `mud/mob_cmds.py:1270-1277` (`do_mpremember`)
- **ROM C**: `src/mob_cmds.c:1155-1164`
- **Gap**: ROM assigns `ch->mprog_target = get_char_world(ch, arg)`
  **unconditionally** for a non-empty argument, so a failed lookup (NULL) clears
  the remembered target. Python early-returned on a failed lookup, leaving a
  stale previous target — `$q`/`$Q` mobprog substitution codes would then
  resolve to a departed character.
- **Fix**: assign `_find_char_world(target_name)` unconditionally for non-empty
  args; the empty-arg `bug()` branch still leaves the target untouched.
- **Tests**: `tests/integration/test_mob_cmds_remember.py` (4 new, incl. the
  failing-before clears-stale-target case). mob_cmds + mobprog suites: 91/91.
- **Sibling sweep**: grepped all `get_char_world`/`get_char_room`/`get_obj_here`
  assignments in `src/mob_cmds.c` — line 1160 is the only one assigning to a
  *persistent* field; every other assigns to a local and guard-returns on NULL
  (which Python mirrors correctly). No sibling divergences in this file.

### `INV-047` — `extract_char` mprog_target quirk (single-path) — ✅ ENFORCED (2.14.25)

- **Python**: `mud/mob_cmds.py:_extract_character`
- **ROM C**: `src/handler.c:2151-2157`
- **Gap**: ROM's `extract_char` `char_list` walk nullifies two single-target
  pointers — `reply` (already mirrored) and `mprog_target`. The latter is a
  faithfully-replicated 2.4b6 quirk: it tests `ch->mprog_target == wch` (the
  *extracted* char's target) and clears `wch->mprog_target` (that target's OWN
  pointer) — so it wipes the remembered target of whoever the extracted char was
  targeting and does NOT clear mobs pointing AT the extracted char. Python left
  it a `# would go here if needed` TODO.
- **Fix**: mirror the buggy line verbatim (not the "corrected"
  `wch->mprog_target == ch` form).
- **Tests**: `tests/integration/test_inv047_extract_clears_mprog_target.py` (2 —
  pins both halves).

### `INV-047` (multi-path) — cleanup on every extract path — ✅ ENFORCED (2.14.26)

- **Python**: `mud/combat/death.py:clear_extract_target_refs` (new shared helper);
  wired into `mob_cmds.py:_extract_character`,
  `game_loop.py:_auto_quit_character` (link-dead/void-quit leg), and
  `connection.py:_disconnect_extract_cleanup` (telnet + websocket clean-disconnect).
- **ROM C**: `src/handler.c:2151-2157` (one `extract_char`).
- **Gap**: ROM has a single `extract_char`; the Python port split extraction
  across call sites, so the PC-quit and socket-disconnect legs leaked dangling
  `reply`/`mprog_target` pointers — the same multi-path class INV-020 closed for
  `nuke_pets`/`die_follower`. The single-path 2.14.25 fix only covered
  `_extract_character`.
- **Fix**: extract the cleanup into `clear_extract_target_refs` and invoke it
  from all three extract paths (ROM loop-then-unlink order preserved).
- **Tests**: `tests/integration/test_inv047_extract_paths_clear_refs.py` (4 —
  quit leg ×2 + disconnect leg ×2). Broader extract/death suites: 38/38.

### `INV-020` step (iv) — `stop_fighting(both=True)` on quit + disconnect legs — ✅ ENFORCED (2.14.27)

- **Python**: `mud/game_loop.py:_auto_quit_character`,
  `mud/net/connection.py:_disconnect_extract_cleanup`.
- **ROM C**: `src/handler.c:2121` (final step of the `extract_char` cleanup chain).
- **Gap**: ROM's `extract_char` ends with `stop_fighting(ch, TRUE)` — `fBoth`
  clears `fighting` on the extracted char AND every char fighting it. The
  mob-extract leg (`_extract_character`) already did this, but the two PC-extract
  legs (link-dead void-quit, socket disconnect) ran only steps i–iii + the
  INV-047 ref-clear, leaving a mob with a dangling `fighting` pointer at the
  unlinked PC — dereferenced on the next combat tick. Found by walking ROM's
  4-step chain against each Python extract path (the same multi-path audit that
  produced INV-047); INV-020's own row enumerated step (iv) but the quit/disconnect
  legs silently omitted it.
- **Fix**: both legs now call `stop_fighting(char, both=True)` after the INV-047
  ref-clear, before the room/registry unlink (ROM loop-then-unlink order). All
  four extract legs now run the full chain.
- **Tests**: `tests/integration/test_inv020_extract_quit_cleanup.py` (+2:
  `test_void_quit_stops_attackers_fighting`,
  `test_disconnect_stops_attackers_fighting`; file now 6/6). Targeted
  extract/fighting regression: 56/56.

### `INV-020` step (v) — extract carried + worn objects on every non-death extract leg — ✅ ENFORCED (2.14.28)

- **Python**: `mud/combat/death.py:extract_carried_objects` (new shared helper),
  wired into `mud/game_loop.py:_auto_quit_character`,
  `mud/net/connection.py:_disconnect_extract_cleanup`,
  `mud/mob_cmds.py:_extract_character`.
- **ROM C**: `src/handler.c:2123-2127` (the `for (obj = ch->carrying; …) extract_obj(obj)`
  loop — step (v) of `extract_char`).
- **Gap**: ROM frees every object on `ch->carrying`, which includes **worn**
  items (equipment only carries an extra `wear_loc`). Python splits inventory
  and equipment into `char.inventory` + the `char.equipment` dict, so a faithful
  "extract all carrying" must drain BOTH. The quit/disconnect legs extracted
  *nothing*, and the mob/`do_purge` leg looped `victim.inventory` only — so a
  quitting/disconnecting PC, and any purged mob with equipment, left carried +
  worn objects lingering in `object_registry` forever (phantom-object leak,
  INV-046 class on the extract path). The death leg is unaffected: `make_corpse`
  moves eq+inv into the corpse before `raw_kill` extracts the char, so its carry
  list is already empty.
- **Fix**: `extract_carried_objects(victim)` drains `victim.inventory` then
  `equipment.values()` via `_extract_obj`; the mob leg's inventory-only loop was
  replaced with the helper call. Discovered the mob-leg equipment leak while
  wiring the PC legs — folded into the same commit (same step-(v) invariant
  across all three non-death paths) rather than filed as a separate MOBCMD row,
  mirroring how INV-047 and INV-020 step (iv) were closed multi-path.
- **Tests**: `tests/integration/test_inv020_quit_extracts_objects.py` (4:
  `test_void_quit_extracts_inventory_objects`,
  `test_void_quit_extracts_equipped_objects`,
  `test_disconnect_extracts_carried_objects`,
  `test_mob_extract_drains_inventory_and_equipment`). Targeted
  extract/fighting/purge regression: 16/16.

### `INV-048` — auto-assist is `violence_update`-only; `aggr_update` must not assist — ✅ ENFORCED (2.14.29)

- **Python**: `mud/ai/aggressive.py:aggressive_update` (removed the inline
  `check_assist` call); contract spans `mud/game_loop.py:violence_tick`,
  `mud/combat/assist.py:check_assist`, `mud/combat/engine.py:multi_hit`.
- **ROM C**: `src/update.c:1136` (aggr_update's bare `multi_hit`) vs
  `src/fight.c:90` (the sole `check_assist` site, inside `violence_update`).
- **Gap**: ROM calls `check_assist` from exactly one place — `violence_update`,
  once per fighting char per `PULSE_VIOLENCE`. `aggr_update` just does
  `multi_hit(ch, victim, TYPE_UNDEFINED)` and never assists, so an aggressive
  mob's room-mates only join the fight on the NEXT violence tick. Python's
  `aggressive_update` erroneously called `check_assist` inline (its comment
  mis-cited `fight.c:90`, which is the *violence_update* site, as if it belonged
  to `aggr_update`), starting assists a full tick early and drawing extra
  `number_bits`/`number_range` coins from the shared MM RNG stream — desyncing
  every subsequent draw in that pulse. Found by probe-then-scope: read the full
  `aggr_update` (already faithful for iteration order/checks/victim reservoir
  after INV-045), noticed the trailing `check_assist` had no ROM counterpart,
  confirmed via `grep check_assist src/fight.c` that the only call site is line
  90 in `violence_update`.
- **Fix**: deleted the inline `check_assist` (+ its local import) from
  `aggressive_update`, leaving the bare `multi_hit(mob, victim)`. `check_assist`
  now fires only from `game_loop.violence_tick` (mirroring `fight.c:90`), as ROM
  does. Filed as INV-048 (cross-module ownership contract).
- **Tests**: `tests/integration/test_mob_ai.py::TestAggressiveUpdateDoesNotAssist`
  (1, spy-asserts `aggressive_update` never invokes `check_assist` while still
  firing aggression). Full `test_mob_ai.py` 18/18; combat/game-loop regression
  (`test_group_combat`, `test_game_loop`, `test_game_loop_order`,
  `test_gl028_mob_spell_effect_tick`) 44 passed/1 skipped.

### `GL-044` — ✅ FIXED (mobile_update wander uses `number_bits(5)`, not `number_door()`)

- **Python**: `mud/ai/__init__.py:_maybe_wander` (direction draw).
- **ROM C**: `src/update.c:498` (`(door = number_bits(5)) <= 5`) vs the wrongly
  borrowed `src/db.c:3541` `number_door` (do_flee/do_mpflee primitive).
- **Gap**: ROM's wander draws a single 5-bit value and **aborts the whole
  wander when it exceeds 5** — an eligible mob wanders only 6/32 of those ticks.
  Python used `rng_mm.number_door()`, which re-rolls with a 3-bit mask until ≤5
  and therefore always returns a valid direction, never aborting. Two
  divergences: (a) mobs wandered ~5× too often (never bailing on a >5 roll);
  (b) `number_door`'s reroll loop consumes a *variable* number of MM-stream
  words (vs exactly one for `number_bits(5)`), desyncing every downstream roll
  that tick. The stale comment mis-cited `mob_cmds.c:1274` (the flee path)
  instead of the real `update.c:498` wander site. Found by probe-then-scope:
  read `mobile_update`'s wander block in ROM, compared the RNG primitive.
- **Fix**: `door = rng_mm.number_bits(5); if door > 5: return`, mirroring ROM.
  Filed as the local single-function divergence `GL-044` in `UPDATE_C_AUDIT.md`
  (wrong RNG primitive — not cross-file, so no INV row).
- **Tests**: `tests/integration/test_mob_ai.py::TestMobileWanderUsesNumberBits5`
  (1, RED→GREEN: door roll 10 > 5 → mob stays put). Full `test_mob_ai.py`
  19/19; game-loop + group-combat regression 43 passed/1 skipped.

### `INV-049` — ✅ ENFORCED (spec_fun dispatched inside `mobile_update`, gated + suppressing)

- **Python**: `mud/ai/__init__.py:mobile_update` (new `run_spec_fun(mob)`
  dispatch inside the per-mob loop), `mud/spec_funs.py` (new
  `_resolve_spec_fun` / `run_spec_fun`; `run_npc_specs` demoted to test/manual
  entry point), `mud/game_loop.py` (removed the `run_npc_specs()` call +
  import from `game_tick`).
- **ROM C**: `src/update.c:425-431` — `(*ch->spec_fun)(ch)` is called INSIDE the
  `mobile_update` per-mob loop, after the charm/empty-area gates and before
  shop-gold, TRIG_DELAY/TRIG_RANDOM, the `position != POS_STANDING` gate,
  scavenge, and wander; a TRUE result `continue`s.
- **Gap**: Python ran `run_npc_specs()` as a separate pass over `room_registry`
  *after* the whole `mobile_update` loop. That (a) bypassed the
  `!IS_NPC || in_room==NULL || AFF_CHARM` and `area->empty && !ACT_UPDATE_ALWAYS`
  gates — charmed mobs and mobs in empty areas still ran their spec; (b) dropped
  the TRUE-result suppression — a spec returning TRUE no longer skipped the rest
  of that mob's tick (scavenge/wander still fired); (c) reordered the shared
  Mitchell-Moore RNG draws — a spec's rolls no longer interleaved per-mob with
  scavenge/wander, desyncing the stream. Found by probe-then-scope: read
  `mobile_update`'s spec-dispatch position in ROM, compared against the Python
  game-tick ordering.
- **Fix**: `mobile_update` now calls `run_spec_fun(mob)` at the ROM position
  (after the gates, before shop-gold) and `continue`s on TRUE; `run_npc_specs()`
  is retained ungated as a test/manual entry point and no longer called from
  `game_tick`. Filed as INV-049 (cross-module dispatch-ordering contract).
- **Tests**: `tests/integration/test_mob_ai.py::TestMobileUpdateDispatchesSpecFun`
  (2: TRUE-result suppresses wander; charmed mob's spec is skipped). Stale
  `run_npc_specs` monkeypatches removed from `test_game_loop_order.py` (×2) and
  `test_mobprog_triggers.py` (×1). Full suite 5676 passed / 4 skipped.

### `EAT-006` — ✅ FIXED (do_eat restores conditions via `gain_condition`, not an inline clamp)

- **Python**: `mud/commands/consumption.py:do_eat` (FOOD branch).
- **ROM C**: `src/act_obj.c:1326-1327` (`gain_condition(COND_FULL, value[0])` /
  `gain_condition(COND_HUNGER, value[1])`); guard logic in
  `src/update.c:367-377` (`gain_condition`).
- **Gap**: `do_eat`'s FOOD branch reimplemented the satiation clamp inline as
  `condition[i] = min(48, condition[i] + value)`. That bypassed two guards baked
  into `gain_condition`: (a) the `level >= LEVEL_IMMORTAL` early-return — an
  immortal eating food had FULL/HUNGER bumped where ROM leaves them untouched;
  (b) the `condition == -1` permanent-satiation sentinel — a -1 ("off") slot was
  clobbered to `min(48, -1+value)` (e.g. `4`) instead of staying -1. `do_drink`
  (DRINK-004) already delegated to `gain_condition` correctly — the two sibling
  commands diverging on the same mechanic was the tell. Found by probe-then-scope
  while reading the consumption surface for position/condition transitions.
- **Fix**: the FOOD branch now calls
  `gain_condition(ch, Condition.FULL, value[0])` and
  `gain_condition(ch, Condition.HUNGER, value[1])`, matching `do_drink` and ROM;
  the "no longer hungry" / "You are full" message logic still reads the slot
  before/after. Local single-function divergence → filed as `EAT-006` in
  `ACT_OBJ_C_AUDIT.md` (no INV — does not cross modules).
- **Tests**: `tests/integration/test_consumables.py::test_eat_food_does_not_change_immortal_conditions`
  and `::test_eat_food_respects_permanent_condition_sentinel` (2, RED→GREEN).
  Full `test_consumables.py` 53/53; INV-025 consumption dispatch 2/2.

### `WIZ-052` — ✅ FIXED (do_mstat condition line reads `COND_*` enum slots, not display order)

- **Python**: `mud/commands/imm_search.py:do_mstat` (condition display, ~line 1126).
- **ROM C**: `src/act_wiz.c:1637-1641` — `"Thirst: %d  Hunger: %d  Full: %d  Drunk: %d"`
  ← `condition[COND_THIRST]`, `condition[COND_HUNGER]`, `condition[COND_FULL]`,
  `condition[COND_DRUNK]`.
- **Gap**: `do_mstat` read the `pcdata.condition` array **positionally by display
  order** — `condition[0]`→thirst, `[1]`→hunger, `[2]`→full, `[3]`→drunk. But the
  array is keyed by the `COND_*` enum (`DRUNK=0, FULL=1, THIRST=2, HUNGER=3`,
  `mud/models/constants.py` `Condition`), so each label printed a *different*
  condition's value: Thirst showed the DRUNK slot, Hunger the FULL slot, Full the
  THIRST slot, Drunk the HUNGER slot. Invisible until the four slots hold distinct
  values. Surfaced by a post-EAT-006 sibling sweep ("re-grep for other sites that
  index `condition[]` by hand") — the same recall-oracle discipline that found
  EAT-006's sibling discrepancy.
- **Fix**: read each label from its enum slot —
  `drunk=condition[Condition.DRUNK]`, `full=condition[Condition.FULL]`,
  `thirst=condition[Condition.THIRST]`, `hunger=condition[Condition.HUNGER]`
  (bounds checks preserved); added `Condition` to the module import. Local
  single-function divergence → filed as `WIZ-052` in `ACT_WIZ_C_AUDIT.md`
  (no INV — does not cross modules).
- **Tests**: `tests/integration/test_act_wiz_command_parity.py::test_mstat_condition_line_maps_cond_indices_correctly`
  (1, RED→GREEN; victim `condition=[1,2,3,4]` asserts
  `"Thirst: 3  Hunger: 4  Full: 2  Drunk: 1"`). Full act_wiz parity 122/122.

### `DRINK-010` — ✅ FIXED (do_drink drains `value[1]` on `value[0] > 0`, not only for drink containers)

- **Python**: `mud/commands/consumption.py:do_drink` (final decrement, ~line 304).
- **ROM C**: `src/act_obj.c:1276-1277` — `if (obj->value[0] > 0) obj->value[1] -= amount;`.
- **Gap**: the Python decrement was guarded on
  `item_type == ITEM_DRINK_CON and value[0] > 0`. ROM gates it on `value[0] > 0`
  **alone**, regardless of item type — so a fountain (`ITEM_FOUNTAIN`) with a
  positive capacity drains its `value[1]` in ROM, while the Python's item-type
  clause froze it. Because the FOUNTAIN switch branch has no `value[1] <= 0`
  empty-check (unlike DRINK_CON), ROM lets a draining fountain's `value[1]` go
  negative — a quirk we now replicate. Stock ROM fountains use `value[0] == 0`
  (infinite), so the divergence is invisible for them and only manifests for
  capacity-bearing fountains. Found by the same post-EAT-006 sibling re-read that
  produced WIZ-052: reading `do_drink` end-to-end against ROM after closing its
  sibling `do_eat` (EAT-006). Local single-function divergence → filed as
  `DRINK-010` in `ACT_OBJ_C_AUDIT.md` (no INV — does not cross modules).
- **Fix**: removed the `item_type_int == int(ItemType.DRINK_CON)` clause; the
  decrement now reads `if len(value) > 0 and value[0] > 0: value[1] -= amount`.
- **Tests**: `tests/integration/test_consumables.py::test_drink_from_fountain_with_capacity_decrements_value`
  (1, RED→GREEN; fountain `value=[20,12,...]` → `value[1] < 12`); the existing
  `::test_drink_from_fountain_does_not_decrement` was re-pinned to the
  `value[0]==0` case (still green — ROM also skips it there) with a corrected
  docstring. Full `test_consumables.py` 54/54.

## Next Steps

Cross-file invariants remains the active pass. Remaining candidate probes:

1. **Mob memory / hunt** — `src/fight.c` ATTACK_BACK + the hunt/track loop vs the
   Python AI tick (not yet probed).
2. **Position-transition edges** — `update_pos` / `stop_fighting` ordering across
   damage, sleep, rest, and death (cross-INV candidate).

Confirmed-faithful (do not re-probe without new evidence): weather/time fan-out,
`update_handler` pulse cadence (locked by `tests/test_game_loop_order.py` +
`tests/integration/test_weather_time.py`).
