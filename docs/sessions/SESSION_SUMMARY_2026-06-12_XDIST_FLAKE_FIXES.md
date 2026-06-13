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

### `EAT-007` — ✅ FIXED (do_eat poison level/duration derive from raw `value[0]`)

- **Python**: `mud/commands/consumption.py:do_eat` (poison branch, ~line 130).
- **ROM C**: `src/act_obj.c:1347-1348` — `af.level = number_fuzzy(obj->value[0]);
  af.duration = 2 * obj->value[0];`.
- **Gap**: the Python derived both fields from `value[0] if value[0] else 1`, a
  defensive substitution ROM does not make. For poisoned food with `value[0]==0`
  that produced `duration = 2*1 = 2` and `level = number_fuzzy(1)` where ROM
  yields `duration = 2*0 = 0` and `level = number_fuzzy(0)`. `number_fuzzy` is
  called exactly once on both paths, so the shared Mitchell-Moore stream stays
  aligned — only the argument value diverged, making the fix RNG-safe. Found by
  the post-DRINK-010 sibling re-read (reading `do_eat` end-to-end against ROM
  after closing `do_drink`'s DRINK-010, the same pattern that chained
  EAT-006 → WIZ-052 → DRINK-010). Local single-function divergence → filed as
  `EAT-007` in `ACT_OBJ_C_AUDIT.md`.
- **Fix**: `level_val = obj_value[0] if len(obj_value) > 0 else 0` (raw value[0]);
  `number_fuzzy(level_val)` and `2 * level_val` unchanged.
- **Tests**: `tests/integration/test_consumables.py::test_eat_poison_duration_uses_raw_value0_not_substituted_one`
  (1, RED→GREEN; value[0]=0 → duration 0). Existing
  `::test_eat_poison_affect_uses_rom_duration` (value[0]=5 → duration 10) still
  green, confirming the non-zero path is unaffected. Full `test_consumables.py` 55/55.

### `BRANDISH-007` — ✅ FIXED (do_brandish `check_improve` fires once per affected target)

- **Python**: `mud/commands/magic_items.py:do_brandish` (success branch, per-target loop ~line 248).
- **ROM C**: `src/act_obj.c:2050-2052` — `check_improve(ch, gsn_staves, TRUE, 2)`
  sits *inside* the `for (vch = ch->in_room->people; ...)` loop, after
  `obj_cast_spell`, so each successful cast is its own learn opportunity.
- **Gap**: the Python hoisted `check_improve(ch, "staves", True, 2)` to run once
  *after* the loop. For AoE staves — a TAR_CHAR_OFFENSIVE/DEFENSIVE spell hitting
  N valid targets — ROM calls `check_improve` N times; the Python called it once.
  `check_improve` rolls `number_range(1, 1000)` for PCs (it early-returns for
  NPCs), so the divergence under-counted both the skill-learn rate and the shared
  Mitchell-Moore RNG draw count by N−1, desyncing every subsequent roll that tick.
  Found by the post-EAT-007 magic-item sibling sweep (read `do_quaff`,
  `do_recite`, `do_brandish`, `do_zap` against ROM; the three single-target
  commands have no loop and were confirmed faithful — only `do_brandish` loops).
  Local single-function divergence → filed as `BRANDISH-007` in `ACT_OBJ_C_AUDIT.md`.
- **Fix**: moved the `check_improve(ch, "staves", True, 2)` call inside the
  `for vch` loop, immediately after `_obj_cast_spell` (the failure-branch
  `check_improve(..., False, 2)` was already correctly once-per-brandish).
- **Tests**: `tests/integration/test_consumables.py::test_brandish_check_improve_fires_once_per_affected_target`
  (1, RED→GREEN; PC caster + 2 NPCs, forced offensive target kind + success branch,
  asserts 2 success calls). Magic-item area suite
  (`test_consumables.py` + `test_inv025_magic_items_act_trigger_dispatch.py` +
  `test_spell_casting.py`) 90/90.

### `PICK-001` — ✅ FIXED (do_pick wires check_improve; stale false-✅ corrected)

- **Python**: `mud/commands/doors.py:do_pick` (the registered `pick` command, dispatcher.py:332).
- **ROM C**: `src/act_move.c:872` (failure, FALSE), `:908`/`:946`/`:982` (portal/container/door success, TRUE) — `check_improve(ch, gsn_pick_lock, ...)`.
- **Gap**: `do_pick` shipped with four `# TODO: Implement check_improve(ch,
  gsn_pick_lock, ...)` stubs and never called the function, so the pick-lock skill
  never improved and ROM's `number_range(1,1000)`/`number_percent()` learn draws
  were skipped. Identical class to RECALL-002 (TODO stub never wired). **The
  per-file audit's "do_pick 100% (29/29) COMPLETE — check_improve FIXED" rows
  (items 59/378 + the table rows) were a stale false-✅** — caught by re-reading
  the code, exactly the AGENTS.md "✅ records when someone last checked, not that
  it is still true" anti-pattern. Found by the post-BRANDISH-007 check_improve
  call-site sweep (grepped every `check_improve` site against its ROM context).
- **Fix**: added `from mud.skills.registry import check_improve`; replaced all
  four TODO stubs with `check_improve(char, "pick lock", FALSE/TRUE, 2)`. Corrected
  the false-✅ claims in `ACT_MOVE_C_AUDIT.md` (annotated, not deleted).
- **Tests**: `tests/integration/test_pick001_check_improve.py` (3, RED→GREEN —
  container success TRUE, skill-failure FALSE, door success TRUE; spy on
  `doors.check_improve`, force `number_percent` via module patch). Pick area suite
  (`test_pick001` + `test_pick_broadcasts` + `test_skill_pick_lock_rom_parity`) 17/17.

### `PICK-002` — ✅ FIXED (do_pick WAIT_STATE uses skill beats with UMAX, not +=24)

- **Python**: `mud/commands/doors.py:do_pick` (WAIT_STATE, ~line 570).
- **ROM C**: `src/act_move.c:856` — `WAIT_STATE(ch, skill_table[gsn_pick_lock].beats)`;
  the macro is `ch->wait = UMAX(ch->wait, beats)`, pick-lock beats=12
  (`src/const.c:1739` / `data/skills.json` `lag:12`).
- **Gap**: `do_pick` used `char.wait = getattr(char,"wait",0) + 24` — wrong value
  (24 not 12) and wrong operator (additive, not `UMAX`). A single pick cost double
  the ROM lag; repeated picks stacked wait unboundedly (wait 30 → 54 instead of
  staying 30). Found immediately after PICK-001 — it was the adjacent
  `# TODO: Implement wait state delay based on skill_table[gsn_pick_lock].beats`
  stub in the same function.
- **Fix**: replaced with `apply_wait_state(char, beats)` (the canonical `UMAX`
  helper at `mud/utils/timing.py`), `beats` sourced data-driven from
  `skill_registry.skills["pick lock"].beats` (fallback 12).
- **Tests**: `tests/integration/test_pick002_wait_state.py` (2, RED→GREEN —
  wait==12 after a pick; UMAX preserves a pre-existing wait==30). Pick area suite 19/19.

### `ORDER-002` — ✅ FIXED (do_order applies WAIT_STATE on a landed order)

- **Python**: `mud/commands/group_commands.py:do_order` (both the `all` and single-target tails).
- **ROM C**: `src/act_comm.c` — `if (found) { WAIT_STATE(ch, PULSE_VIOLENCE); send_to_char("Ok.\n\r", ch); }`; `PULSE_VIOLENCE` == 12 (`src/merc.h:155-156`).
- **Gap**: both Python branches returned `"Ok."` with no lag — the all-branch had
  an explicit `# Note: WAIT_STATE not implemented yet` stub. So an orderer could
  spam orders with zero wait. **The audit doc's "✅ WAIT_STATE and 'Ok.'
  confirmation" row was a stale false-✅** (corrected in `ACT_COMM_C_AUDIT.md`).
  Found by the WAIT_STATE-placeholder sweep that followed PICK-002 (grepped
  `not implemented yet` / `Placeholder` across `mud/`).
- **Fix**: `apply_wait_state(char, get_pulse_violence())` before both `"Ok."`
  returns. The no-follower path correctly stays lag-free (ROM only sets WAIT_STATE
  inside `if (found)`).
- **Tests**: `tests/integration/test_order002_wait_state.py` (3, RED→GREEN —
  single-target wait==12, `order all` wait==12, no-follower wait==0). Order area
  suite (`test_order002` + `test_order_broadcasts`) 5/5.

### `ORDER-003` — ✅ FIXED (do_order single-target gate adds the immortal-trust clause)

- **Python**: `mud/commands/group_commands.py:do_order` (single-target "Do it yourself!" gate).
- **ROM C**: `src/act_comm.c` — `if (!IS_AFFECTED(victim, AFF_CHARM) || victim->master != ch || (IS_IMMORTAL(victim) && victim->trust >= ch->trust))`.
- **Gap**: Python checked only the first two clauses, omitting
  `IS_IMMORTAL(victim) && victim->trust >= ch->trust`, so a charmed immortal whose
  trust ≥ the orderer's could be ordered where ROM refuses. Filed alongside
  ORDER-002, closed immediately after (full context in hand).
- **Fix**: added `victim.is_immortal() and victim.trust >= char.trust` to the gate.
  `Character.is_immortal()` mirrors ROM `IS_IMMORTAL` (`get_trust >= LEVEL_IMMORTAL`
  = 52), so a normal charmed mob (`is_immortal()` False) is unaffected and stays
  orderable.
- **Tests**: `tests/integration/test_order003_immortal_trust.py` (2, RED→GREEN —
  refuses a charmed immortal with trust≥orderer; still allows a normal charmed mob).

### `SAVE-001` — ✅ FIXED (do_save applies WAIT_STATE(ch, 4 * PULSE_VIOLENCE))

- **Python**: `mud/commands/session.py:do_save`.
- **ROM C**: `src/act_comm.c:1522-1532` — `save_char_obj(ch); send_to_char("Saving. ...\n\r", ch); WAIT_STATE(ch, 4 * PULSE_VIOLENCE);` (== 48).
- **Gap**: `do_save` saved and returned the message but applied no WAIT_STATE, so
  `save` could be spammed with zero lag. **Audit doc's "save_char_obj() +
  WAIT_STATE ✅ 100%" row was a stale false-✅** (corrected). Found by enumerating
  every ROM `WAIT_STATE(ch, <fixed>)` site in the act_* files and cross-checking
  the Python equivalent — `move_char` (wait 1) and `do_recall` (wait 4) were
  already faithful; `do_save` was the miss.
- **Fix**: `apply_wait_state(ch, 4 * get_pulse_violence())` after the save+message
  (UMAX; no-save-failure path returns early, as ROM only reaches WAIT_STATE on a
  successful save).
- **Tests**: `tests/integration/test_save001_wait_state.py` (2, RED→GREEN —
  wait==48 after save; UMAX preserves a pre-existing wait==100).

### `PASSWORD-001` — ✅ FIXED (do_password wrong-password WAIT_STATE uses UMAX)

- **Python**: `mud/commands/character.py:do_password` (wrong-password branch).
- **ROM C**: `src/act_info.c:2895` — `WAIT_STATE(ch, 40)` = `UMAX(ch->wait, 40)`.
- **Gap**: Python set `ch.wait = 40` (plain assignment), *lowering* a higher
  existing wait to 40. Sibling of SAVE-001 from the same ROM-WAIT_STATE-site
  cross-check; same UMAX-vs-assign class as PICK-002. The `do_password` row was
  marked "100% COMPLETE" but missed this (annotated in `ACT_INFO_C_AUDIT.md`).
- **Fix**: `apply_wait_state(ch, 40)`.
- **Tests**: `tests/integration/test_password001_wait_state_umax.py` (2, RED→GREEN —
  wait==40 from zero; UMAX preserves a pre-existing wait==100).

### `CAST-010` — ✅ FIXED (do_cast WAIT_STATE uses the spell's beats, not flat PULSE_VIOLENCE)

- **Python**: `mud/commands/combat.py:do_cast` (cast-lag, before the success roll).
- **ROM C**: `src/magic.c:547` — `WAIT_STATE(ch, skill_table[sn].beats)`.
- **Gap**: Python applied a flat `get_pulse_violence()` (==12) for every spell.
  Spell beats vary — 81 spells at 12, but **34 differ** (22@24, 7@18, 4@36, 1@20:
  fly=18, enchant armor=24, mass healing=36) and 19 are 0. So a third of all spells
  got the wrong cast lag (slower spells cast too fast; beats-0 spells over-lagged).
  This was the deepest find of the ROM-WAIT_STATE-site cross-check — the only one
  outside the simple "missing/assign" class, since it's a per-spell *data* lookup
  the flat constant silently flattened.
- **Fix**: `spell_beats = int(getattr(skill, "beats", 0) or getattr(skill, "lag", 0) or 0)`;
  `_apply_wait_state(char, spell_beats)`. ROM uses the **raw** beats (no HASTE/SLOW
  for casting), so this reads `skill.beats` directly rather than via
  `_compute_skill_lag`; `_apply_wait_state` treats 0 as a UMAX no-op = ROM
  `WAIT_STATE(ch, 0)`.
- **Tests**: `tests/integration/test_cast010_wait_state_uses_spell_beats.py` (1,
  RED→GREEN — casting `fly` (beats 18) sets wait 18, not 12). Spell-casting +
  cast-listing suites 45/45.

### `CAST-011` — ✅ FIXED (do_cast broadcasts the spell incantation to the room)

- **Python**: `mud/commands/combat.py:do_cast` (before the WAIT_STATE block).
- **ROM C**: `src/magic.c:544-545` — `if (str_cmp(skill_table[sn].name, "ventriloquate")) say_spell(ch, sn);` (say_spell broadcast: `src/magic.c:199-204`).
- **Gap**: `do_cast` never broadcast the incantation, so casting was *silent* to the
  room — other players never saw `"$n utters the words, '...'"`. The Python port
  already had a complete `broadcast_spell_words` helper (`mud/skills/say_spell.py`,
  class-based garbling + INV-001 single-delivery) but only a **test** called it;
  the command flow didn't. Found by probing the do_cast flow right after CAST-010.
- **Fix**: `do_cast` now calls `broadcast_spell_words(char, skill.name)` before the
  WAIT_STATE, gated by `skill.name.lower() != "ventriloquate"` (ROM's `str_cmp`
  exclusion). Placed after the PK gates (a safety-blocked cast returns before it,
  as in ROM). Caster receives nothing (FINDING-013 silent-on-success preserved —
  `broadcast_spell_words` targets other occupants only).
- **Tests**: `tests/integration/test_cast011_say_spell_broadcast.py` (2, RED→GREEN —
  normal spell broadcasts the spell name; ventriloquate is excluded). Cast/spell
  regression suites 78/78.

### `PRACTICE-001` — ✅ FIXED (do_practice failure-gate ordering matches ROM)

- **Python**: `mud/commands/advancement.py:do_practice`.
- **ROM C**: `src/act_info.c` — order after IS_AWAKE: find ACT_PRACTICE mob (→ "You
  can't do that here."), THEN `practice <= 0` (→ "no practice sessions left"), THEN
  spell validity (→ "You can't practice that.").
- **Gap**: Python checked `practice <= 0` and `find_spell`/skill-validity *before*
  the trainer-presence gate. So a player **not at a trainer** who *also* had 0
  practices (or named an invalid skill) saw "You have no practice sessions left." /
  "You can't practice that." where ROM shows "You can't do that here." (The single-
  failure cases already matched — a valid skill + practices but no trainer reached
  the trainer gate either way.) Found by re-verifying the "do_practice 100%
  COMPLETE" audit row against source — the same stale-✅ re-verification vein that
  produced PICK-001/ORDER-002/SAVE-001/PASSWORD-001.
- **Fix**: moved the `_find_practice_trainer` gate to immediately after the
  `is_awake()` check (ROM order: awake → trainer → sessions → spell-valid).
- **Tests**: `tests/integration/test_do_practice_command.py` (2 new, RED→GREEN —
  no-trainer+0-practices and no-trainer+invalid-skill both → "You can't do that
  here."). Existing 16 practice tests unaffected (their session/invalid-skill cases
  all have a trainer present). Practice suites 42/42.

### `CONSIDER-001` — ✅ FIXED (do_consider capitalizes the act() line)

- **Python**: `mud/commands/consider.py:do_consider`.
- **ROM C**: `src/comm.c:2379` — `act_new` upper-cases `buf[0]`; do_consider
  renders via `act(msg, ch, NULL, victim, TO_CHAR)` (`src/act_info.c`).
- **Gap**: four of the seven difficulty messages begin with `$N` (the victim
  name). ROM's act() caps the first letter of the rendered line, so a lowercase
  mob short_descr ("a fierce goblin") renders capitalized ("A fierce goblin is no
  match for you."). Python baked the raw lowercase short_descr. The "You…"- and
  "The…"/"Death…"-first messages were already correct (literal capital). Found by
  re-verifying the "do_consider 100% COMPLETE" row against source.
- **Fix**: wrap the final message in `capitalize_act_line` (the INV-029
  ACT-FIRST-LETTER-CAP helper). The caster always sees the victim here
  (get_char_room succeeded), so the baked name == ROM's `PERS(victim, ch)`; only
  the buf[0] cap was missing.
- **Tests**: `tests/integration/test_do_consider_command.py::TestDoConsiderCapitalization`
  (2, RED→GREEN — `$N`-first message caps the victim name; "You…"-first message
  keeps the mid-sentence `$N` lowercase). Existing 15 consider tests use `.lower()`
  so unaffected. Consider suite 17/17.

### `REPORT-001` — ✅ FIXED (do_report room broadcast uses the act() system)

- **Python**: `mud/commands/info.py:do_report`.
- **ROM C**: `src/act_info.c:2670` — `act("$n says 'I have ...'", ch, NULL, NULL, TO_ROOM)`.
- **Gap**: the Python room broadcast was a hand-rolled loop with three faults at
  once — (a) baked `char.name` (no `$n` PERS masking, so an invisible reporter
  leaked their name); (b) iterated `other.desc.send` directly, skipping
  descriptor-less occupants (NPC witnesses got no TRIG_ACT, and the INV-001
  single-delivery channel was bypassed); (c) used `other != char` instead of
  `is not`. Found by re-verifying the "do_report 100% COMPLETE" audit row against
  source.
- **Fix**: replaced the loop with `act_to_room(room, "$n says 'I have …'", char)`
  — the canonical helper that applies per-recipient PERS masking (INV-025/027),
  single-delivery (INV-001), and TRIG_ACT dispatch.
- **Tests**: `tests/integration/test_info_display.py::test_report_broadcasts_to_room_via_act_system`
  (RED→GREEN — a descriptor-less observer now receives the `$n`-rendered line).
  Existing 17 info-display tests unaffected. Suite 18/18.

### `FIGHT-062` — ✅ FIXED (do_flee "$n has fled!" broadcast uses the act() system)

- **Python**: `mud/commands/combat.py:do_flee` (success path, fled-from room broadcast).
- **ROM C**: `src/fight.c:3005-3007` — restores `ch->in_room = was_in` and calls
  `act("$n has fled!", ch, NULL, NULL, TO_ROOM)`.
- **Gap**: same class as REPORT-001 — a hand-rolled loop over `was_in.people`
  calling `other.desc.send(f"{char.name} has fled!")`: baked the name (no `$n`
  PERS masking, so an invisible fleer leaked it) and skipped descriptor-less
  occupants (NPC witnesses got no TRIG_ACT; the opponent left behind received
  nothing). Found by sweeping the command layer for `desc.send`/manual
  `for … in room.people` broadcast loops after REPORT-001.
- **Fix**: replaced with `act_to_room(was_in, "$n has fled!", char)`. `char` has
  already moved to `now_in`, so it isn't in `was_in.people`; `exclude=char` is
  harmless and documents ROM's TO_ROOM intent.
- **Tests**: `tests/integration/test_fight062_flee_broadcast.py` (RED→GREEN — a
  descriptor-less witness in the fled-from room receives the `$n`-rendered line).
  Existing flee tests (054/061/043/still-recovering/moves-character) 17/17.

### `COMPARE-001` — ✅ FIXED (do_compare equipped-match requires overlapping wear slots)

- **Python**: `mud/commands/compare.py:_find_equipped_match`.
- **ROM C**: `src/act_info.c:2323-2332` — the arg2-empty branch breaks on the
  first worn item with `obj1->item_type == obj2->item_type && (obj1->wear_flags &
  obj2->wear_flags & ~ITEM_TAKE) != 0`.
- **Gap**: the Python returned the first equipped non-weapon item for ARMOR (and
  only handled WEAPON/ARMOR types), ignoring the wear_flags overlap — so
  "compare ring" compared a WEAR_FINGER ring against a worn WEAR_HEAD helmet,
  where ROM requires a shared wear slot and would say "You aren't wearing anything
  comparable." Found by re-verifying the "do_compare 100% COMPLETE" row; the
  `$p`/`$P` render + ACT-CAP was already correct via `act_format` (unlike
  do_consider).
- **Fix**: rewrote `_find_equipped_match` to iterate `char.equipment.values()`
  (the worn items = ROM's `wear_loc != WEAR_NONE` entries) matching item_type and
  `(obj1_wear & obj2_wear & ~TAKE) != 0`.
- **Tests**: `tests/integration/test_compare_critical_gaps.py` (2, RED→GREEN —
  ring↔helmet (no overlap) is "not comparable"; ring↔ring (WEAR_FINGER overlap)
  renders a real comparison). Existing 10 compare tests (two-explicit-item path)
  unaffected. Compare suite 29/29.

### `EMOTE-005` — ✅ FIXED (emote self-line shows the actor's name, not "You"; reverts EMOTE-002)

- **Python**: `mud/commands/communication.py:do_emote` (TO_CHAR return).
- **ROM C**: `src/act_comm.c:1092` `act("$n $T", ch, NULL, argument, TO_CHAR)` +
  `src/comm.c` `act_new` (`$n` → `PERS(ch, to)`) + `src/merc.h:2145` `PERS`.
- **Gap (a false-premise prior ✅)**: EMOTE-002 (marked CRITICAL ✅ FIXED 2.8.43)
  claimed "TO_CHAR `$n` substitutes to 'You' (act() handles the self branch)" and
  changed the self-line from `f"{char.name} {args}"` to `f"You {args}"`. ROM `act()`
  does **no** `$n`→"You" conversion: `PERS(ch, ch) = can_see(ch, ch) ? name :
  "someone"` = the actor's own name. **Decisive proof:** ROM `do_say` writes a
  *literal* `"You say '%s'"` for its self-line and only uses `act("$n says…")` for
  the room — redundant if `act()` converted `$n`→"You". So stock ROM emote shows
  the emoter their own name (a well-known ROM quirk); EMOTE-002 introduced the
  divergence. Found by re-verifying the EMOTE-002 ✅ against source.
- **Fix**: TO_CHAR return is now `capitalize_act_line(f"{pers(char, char)} {args}")`,
  matching the TO_ROOM leg's PERS render. Marked EMOTE-002 ❌ REVERTED in the audit.
- **Tests**: inverted `test_emote_002_…renders_you_…` → `test_emote_005_…renders_actor_name_not_you`
  (actor "Emoself" now sees "Emoself nods"). Emote + act_comm-gaps suites 32/32.
- **Lesson**: a documented CRITICAL ✅ can itself be the bug — the re-verify-against-source
  rule caught a "fix" that was a misreading of ROM `act()`.

### `TELL-008` — ✅ FIXED (tell status lines use the victim's gendered pronouns)

- **Python**: `mud/commands/communication.py:_validate_tell_target` + `_handle_buffered_tell`.
- **ROM C**: `src/act_comm.c` — `act("$E is not receiving tells.", ch, 0, victim, TO_CHAR)`,
  `act("$E can't hear you.", …)`, `act("$N seems to have misplaced $S link…", …)`,
  the AFK / note-writing lines (all `$E`).
- **Gap**: six teller-facing status lines baked the victim's NAME + "they"/"their"
  where ROM renders the victim's gendered pronouns through `act()` (`$E`=He/She/It,
  `$S`=his/her/its, `$N`=PERS name). So `tell bob hi` (Bob sexless, QUIET) showed
  "Bob is not receiving tells." where ROM shows "It is not receiving tells.", and a
  male linkdead victim showed "…their link…" vs ROM "…his link…". Found by applying
  the EMOTE-005 `$n`/PERS lens to the comm commands. Three existing tests asserted
  the name-based (non-ROM) forms.
- **Fix**: rendered all six via `act_format("$E …"/"$N … $S …", recipient=sender,
  actor=sender, arg2=target)` — `act_format` already supports the pronoun codes and
  caps buf[0]. The linkdead line keeps `$N` (ROM uses the name there) + `$S`.
- **Tests**: inverted 3 `tests/test_communication.py` assertions (sexless Bob →
  "It"/"its") + added `test_tell008_status_messages_use_gendered_pronoun` (male
  victim → "He is not receiving tells.", proving it's pronoun-driven not a string
  swap). Communication suite 18/18.

### `GOSSIP-001` — ✅ FIXED gossip+auction (global channel `$n` PERS-masked per recipient)

- **Python**: `mud/commands/communication.py:do_gossip` + `do_auction`; `mud/net/protocol.py:broadcast_global`.
- **ROM C**: `src/act_comm.c:333` (do_gossip) / `:276` (do_auction) — `descriptor_list`
  walk rendering each listener's copy via `act_new("{d$n gossips '{9$t{d'{x", ch,
  argument, d->character, TO_VICT, POS_SLEEPING)`.
- **Gap**: the Python baked `char.name` into ONE shared message passed to
  `broadcast_global`, so `$n` was never PERS-masked per recipient — a wiz-invis /
  invisible sender leaked their name to every listener (ROM shows "Someone gossips"
  to those who can't see them). Found by extending the EMOTE-005/TELL-008 `$n`/PERS
  lens to the global channels.
- **Fix**: added a backward-compatible `render: recipient -> str` param to
  `broadcast_global` (used per recipient when provided; `message` only when it's
  None). `do_gossip`/`do_auction` pass `render=lambda target:
  capitalize_act_line(f"…{pers(char, target)}…")` — the same proven PERS
  infrastructure behind the room-channel sweep (SAY-002/EMOTE-001).
- **Tests**: `tests/test_communication.py::test_gossip001_invisible_gossiper_masks_to_someone`
  (RED→GREEN — invisible gossiper → listener sees "Someone gossips", name absent).
  Existing channel tests (visible sender → name) 42/42 unaffected.
- **Follow-up done same session as GOSSIP-002** (see below).

### `GOSSIP-002` — ✅ FIXED (grats/quote/question/answer/music PERS-mask `$n`)

- **Python**: `mud/commands/communication.py:do_grats`/`do_quote`/`do_question`/`do_answer`/`do_music`.
- **ROM C**: `src/act_comm.c` — each renders per recipient via
  `act_new("{t$n grats '$t'{x", ch, …, d->character, TO_VICT)` (and the analogous
  `$n quotes/questions/answers/MUSIC` forms).
- **Gap**: same class as GOSSIP-001 — all five baked `char.name` into one shared
  `broadcast_global` message, leaking an invisible/wiz-invis sender's identity.
- **Fix**: applied the GOSSIP-001 `render=lambda target:
  capitalize_act_line(f"…{pers(char, target)}…")` per-recipient PERS pattern to all
  five (the `broadcast_global` `render` infra was already in place from GOSSIP-001).
- **Tests**: `tests/test_communication.py::test_gossip002_invisible_sender_masks_across_global_channels`
  (grats: invisible sender → "Someone grats", name absent). Channel suite 43/43.
- **Left as a low-value edge** (noted in `ACT_COMM_C_AUDIT.md`): `do_clantalk` /
  `do_immtalk` still bake the name — immtalk recipients are holylight-visible
  immortals (PERS == name anyway), clantalk a small mutually-visible audience.

### `GIVE-002` — ✅ FIXED (give rejection lines use the victim's `$N`/`$S` pronouns)

- **Python**: `mud/commands/give.py:do_give`.
- **ROM C**: `src/act_obj.c` — `act("$N has $S hands full.", ch, NULL, victim, TO_CHAR)`,
  `act("$N can't carry that much weight.", …)`, `act("$N can't see it.", …)`,
  `act("$N tells you 'Sorry, you'll have to sell that.'", …)`.
- **Gap**: the four giver-facing rejections baked the victim NAME and used a local
  `_victim_possessive` helper that returned **"their"** for `Sex.NONE` where ROM's
  `$S` is **"its"** — so giving an over-full item to a sexless mob showed "Receiver
  has their hands full." vs ROM "…its hands full." Found extending the
  EMOTE-005/TELL-008 pronoun lens to `act_obj`.
- **Fix**: rendered all four via `act_format("$N has $S hands full.", recipient=char,
  actor=char, arg2=victim)` (etc.) — correct `$N` PERS name + `$S` = its/his/her,
  caps buf[0]; deleted the dead `_victim_name`/`_victim_possessive` helpers.
- **Tests**: inverted the `test_give_command.py` hands-full assertion (sexless →
  "its") + added `test_give002_hands_full_uses_gendered_possessive` (male → "his").
  Give suite 15/15.

### `SAC-006` — ✅ FIXED (sacrifice rejection/furniture messages capitalize via act())

- **Python**: `mud/commands/obj_manipulation.py:do_sacrifice`.
- **ROM C**: `src/act_obj.c` — `act("$p is not an acceptable sacrifice.", ch, obj, 0, TO_CHAR)`
  and `act("$N appears to be using $p.", ch, obj, gch, TO_CHAR)` (act() caps buf[0]).
- **Gap**: both lines baked the lowercase object `short_descr`, so "a blessed relic
  is not an acceptable sacrifice." where ROM caps the first letter ("A blessed
  relic …"). The `$N appears to be using $p` line also skipped PERS. Found applying
  the CONSIDER-001 ACT-CAP / `$N` lens to act_obj.
- **Fix**: rendered both via `act_format("$p …"/"$N appears to be using $p.",
  recipient=char, actor=char, arg1=obj[, arg2=person])` — caps buf[0], $N PERS-masked.
  The `$mself` self-sacrifice reflexive was already faithful (`_object_pronoun(NONE)`
  + "self" = "itself").
- **Tests**: `tests/integration/test_sacrifice_command.py::test_sacrifice006_rejection_capitalizes_object_name`
  (RED→GREEN — "A blessed relic …"). Existing sacrifice + furniture-occupancy tests
  use `.lower()` so unaffected. Sacrifice+furniture suites 13/13.

### `GET-014` — ✅ FIXED (carry-limit message uses `$d` first keyword + capitalization)

- **Python**: `mud/commands/inventory.py:do_get` (carry-number + carry-weight gates).
- **ROM C**: `src/act_obj.c:107,115` — `act("$d: you can't carry that many items./much weight.", ch, NULL, obj->name, TO_CHAR)`.
- **Gap**: ROM `$d` renders the **first keyword** of `obj->name` and `act()` caps
  buf[0]. The Python baked the **full** lowercase `obj.name` keyword string — e.g.
  obj name "relic ancient" → "relic ancient: you can't carry that many items." vs
  ROM "Relic: …". This was the long-standing ⚠️ SIMILAR row in the ACT_OBJ audit
  comparison table (flagged but never closed). Found applying the ACT-CAP/`$d` lens.
- **Fix**: rendered both messages via `act_format("$d: …", recipient=char,
  actor=char, arg2=obj.name)` — `act_format`'s `$d` = `str(arg2).split()[0]` + caps.
- **Tests**: `tests/test_encumbrance.py::test_get014_carry_limit_message_uses_first_keyword_capitalized`
  (multi-word name "relic ancient" → "Relic: …"). Existing encumbrance/shop tests
  use substring `in` so unaffected; shop carry-limit is a separate literal-"You"
  message. Encumbrance+shops+give suites 65/65.

### `FIGHT-063` — ✅ FIXED (backstab "hurt and suspicious" uses `$N` PERS short_descr + cap)

- **Python**: `mud/commands/combat.py:do_backstab`.
- **ROM C**: `src/fight.c:2946` — `act("$N is hurt and suspicious ... you can't sneak up.", ch, NULL, victim, TO_CHAR)`.
- **Gap**: the message baked `victim.name` (the keyword string) lowercase, but ROM
  `$N` = `PERS(victim, ch)` = the NPC **short_descr** (capitalized buf[0]). A
  wounded mob with name "goblin sneaky" / short_descr "a sneaky goblin" showed
  "goblin sneaky is hurt …" vs ROM "A sneaky goblin is hurt …" (and an invisible
  victim would mask to "Someone"). Found applying the `$N`/PERS/ACT-CAP lens to fight.c.
- **Fix**: `act_format("$N is hurt and suspicious ... you can't sneak up.",
  recipient=char, actor=char, arg2=victim)`.
- **Tests**: `tests/test_skill_combat_rom_parity.py::TestBackstabRomParity::test_backstab063_hurt_message_uses_pers_shortdescr_capitalized`
  (RED→GREEN — short_descr rendered capitalized). Existing backstab test uses
  `.lower()` substring so unaffected. Backstab suite 14/14.

### `FIGHT-064` — ✅ FIXED (kill/murder safety messages use `$N` PERS short_descr)

- **Python**: `mud/commands/combat.py:_kill_safety_message` + `mud/commands/murder.py:_murder_safety_check` (two near-identical copies).
- **ROM C**: `src/fight.c:1061` `act("But $N looks so cute and cuddly...", …)` + `:2707/:2805/:2873` `act("$N is your beloved master.", ch, NULL, victim, TO_CHAR)`.
- **Gap**: both messages baked `victim.name` (keyword string) where ROM `$N` =
  `PERS(victim)` = NPC short_descr (capitalized buf[0] for the beloved-master line,
  which begins with `$N`). A charmed PC killing NPC master "wizard"/short_descr
  "a dark wizard" saw "wizard is your beloved master." vs ROM "A dark wizard is your
  beloved master." 4 sites (2 functions × 2 messages). Found applying the
  `$N`/PERS/ACT-CAP lens to the is_safe family.
- **Fix**: all four via `act_format("$N …", recipient=char, actor=char, arg2=victim)`.
  PC masters (PERS=name) and the literal `send_to_char` guards ("don't own that
  monster", "leave them alone", "Pick on someone") are unchanged.
- **Tests**: `tests/test_combat.py::test_fight064_beloved_master_message_uses_pers_shortdescr_capitalized`
  (NPC master → "A dark wizard …"). Existing PC-master test (test_combat.py:209,
  "Master is your beloved master.") and the `.lower()` pet/murder-safety tests stay
  green. Combat+skill-combat+safety suites 151/151.

### `TRIP-001` — ✅ FIXED (do_trip blocking messages use `$S`/`$N` ROM pronouns)

- **Python**: `mud/skills/handlers.py:trip`.
- **ROM C**: `src/fight.c` `do_trip` — `act("$S feet aren't on the ground.", …)`,
  `act("$N is already down.", …)`, `act("$N is your beloved master.", …)`.
- **Gap**: three messages baked literal "Their"/"They" or the keyword name where
  ROM uses `$S` (his/her/its, capitalized at start) and `$N` (PERS short_descr,
  capitalized). The beloved-master line even said "They **are**" vs ROM "$N **is**".
  The handler already used `act_format` for its disarm/dirt-kick lines, so this was
  a self-inconsistency. Found applying the `act()`-rendering lens to fight.c skills.
- **Fix**: all three via `act_format("$S …"/"$N …", recipient=caster, actor=caster, arg2=victim)`.
- **Tests**: `tests/test_skills_combat.py::test_trip001_messages_use_rom_pronoun_and_pers`
  (male flyer → "His feet aren't on the ground."; already-down NPC → "A sneaky
  goblin is already down." — used an INSIDE/lit room so `can_see`/PERS resolves the
  short_descr rather than masking to "Someone"). Existing trip tests use substring
  so unaffected. Skill-combat suites 112/112.

### `MAGIC-016` — ✅ FIXED (armor spell cross-target lines use `$N` PERS short_descr)

- **Python**: `mud/skills/handlers.py:armor`.
- **ROM C**: `src/magic.c:763` `act("$N is already armored.", …)` + `:776` `act("$N is protected by your magic.", …)`.
- **Gap**: both cross-target TO_CHAR lines baked `_character_name(target)` (the
  keyword `name` for an NPC) where ROM `$N` = PERS = NPC short_descr (capitalized).
  Casting armor on NPC "goblin"/"a green goblin" showed "goblin is protected by your
  magic." vs ROM "A green goblin is protected by your magic." Self-cast and PC-victim
  lines were already correct (PERS=name). Found applying the `act()`-rendering lens
  to the spell handlers.
- **Fix**: both via `act_format("$N …", recipient=caster, actor=caster, arg2=target)`.
- **Tests**: `tests/integration/test_magic_002_armor_message.py::test_magic016_armor_cross_target_npc_uses_pers_shortdescr_capitalized`
  (NPC → "A green goblin is protected by your magic."). Existing PC-victim ("Bob")
  tests stay green. Armor+buffs suites 30/30.
- **⚠️ Filed for next agent (MAGIC-016 cluster):** the identical baked-name pattern
  recurs across many spell handlers — `shield`, `frenzy`/divine-favor (magic.c:845/863),
  `change_sex` (magic.c:1321 — replicate the **literal `(?)` ROM quirk** + `$s`),
  cure_blindness/disease/poison "doesn't appear to be …" lines (~2703/2759/2814),
  curse-object "glows with a … aura" lines (~2874/2887/2891, `$p`). Each needs its
  ROM `act()` code verified before conversion. See the MAGIC-016 row in `MAGIC_C_AUDIT.md`.

### `MAGIC-017` — ✅ FIXED (shield spell TO_CHAR + TO_ROOM lines use PERS)

- **Python**: `mud/skills/handlers.py:shield`.
- **ROM C**: `src/magic.c` `spell_shield` — `act("$N is already protected by a shield.", …, TO_CHAR)` + `act("$n is surrounded by a force shield.", victim, NULL, NULL, TO_ROOM)`.
- **Gap**: combined MAGIC-016 (TO_CHAR baked name) + MAGIC-014 (hand-rolled TO_ROOM
  loop) in one handler. The "already protected" line baked the keyword name; the
  success room broadcast iterated `room.people` baking `target.name` with a
  "Someone" fallback (visible NPC → "Someone …"; invisible actor leaked its name).
  ROM renders `$N`/`$n` = PERS short_descr, capitalized; invisible → "someone".
- **Fix**: TO_CHAR via `act_format("$N …", arg2=target)`; TO_ROOM via
  `act_to_room(room, "$n is surrounded by a force shield.", target, exclude=target)`.
- **Tests**: `tests/integration/test_magic017_shield_pers.py` (NPC room broadcast →
  "A green goblin is surrounded by a force shield."; already-protected TO_CHAR →
  "A green goblin is already protected by a shield."). Shield+buffs suites 27/27.
- Continues the **MAGIC-016 cluster** — shield struck off; frenzy/divine-favor,
  change_sex (literal `(?)` quirk), cures, curse-object still OPEN.

### `MAGIC-018` — ✅ FIXED (bless spell cross-target lines use `$N` PERS short_descr)

- **Python**: `mud/skills/handlers.py:bless`.
- **ROM C**: `src/magic.c:845` `act("$N already has divine favor.", …, TO_CHAR)` + `:863` `act("You grant $N the favor of your god.", …, TO_CHAR)`.
- **Gap**: both baked `_character_name(victim)` (keyword name for an NPC) where ROM
  `$N` = PERS = short_descr (capitalized for the "$N already…" line). Casting bless
  on NPC "goblin"/"a green goblin" showed "You grant goblin the favor of your god."
  vs ROM "You grant a green goblin the favor of your god." Self-cast / PC victims
  already correct. Continues the MAGIC-016 cluster.
- **Fix**: both via `act_format("$N …"/"You grant $N …", arg2=victim)`.
- **Tests**: `tests/integration/test_magic018_bless_pers.py` (NPC → "A green goblin
  already has divine favor." + "You grant a green goblin the favor of your god.").
  Note: bless is a cleric spell — the test caster uses `ch_class=1` (level 7 req),
  not 2 (level 53). Buffs/heal/bless suites 34/34.
- **MAGIC-016 cluster status**: armor ✅, shield ✅, bless ✅ — **still OPEN**:
  change_sex (literal `$s(?)` quirk), cure_blindness/disease/poison, curse-object.

### `MAGIC-019` — ✅ FIXED (cure_blindness/disease/poison "doesn't appear to be …" use `$N` PERS)

- **Python**: `mud/skills/handlers.py:cure_blindness`/`cure_disease`/`cure_poison`.
- **ROM C**: `src/magic.c:1608/1650/1694` — `act("$N doesn't appear to be blinded/diseased/poisoned.", ch, NULL, victim, TO_CHAR)`.
- **Gap**: all three baked the victim's keyword `name` where ROM `$N` = PERS = NPC
  short_descr (capitalized). Curing a non-blind NPC "goblin"/"a green goblin" showed
  "goblin doesn't appear to be blinded." vs ROM "A green goblin doesn't appear to be
  blinded." Self-cast lines were already correct.
- **Fix**: all three via `act_format("$N doesn't appear to be …", arg2=victim)`;
  dropped the dead `name = …` locals.
- **Tests**: `tests/integration/test_magic019_cure_pers.py` (3 — blindness/disease/
  poison → "A green goblin doesn't appear to be …"; direct handler calls bypass the
  do_cast class/level setup). Healing suites 27/27.
- **MAGIC-016 cluster status**: armor ✅, shield ✅, bless ✅, cures ✅ — **still
  OPEN**: change_sex (literal `$s(?)` quirk), curse-object aura lines.

### `MAGIC-020` — ✅ FIXED (curse-object `$p` capitalization + TO_ALL aura broadcast)

- **Python**: `mud/skills/handlers.py:curse` (object branch).
- **ROM C**: `src/magic.c:1737` `act("$p is already filled with evil.", …, TO_CHAR)`,
  `:1751/:1773` `act("$p glows with a red/malevolent aura.", …, TO_ALL)`, `:1758`
  `act("The holy aura of $p is too powerful…", …, TO_CHAR)`.
- **Gap**: baked the lowercase `obj.short_descr` (no buf[0] cap) AND sent the aura
  lines TO_CHAR-only where ROM uses **TO_ALL** (room + caster). Cursing "a silver
  dagger" showed "a silver dagger glows with a malevolent aura." to the caster alone
  vs ROM "A silver dagger glows with a malevolent aura." to the whole room.
- **Fix**: TO_CHAR lines via `act_format("$p …", arg1=obj)` (caps + `can_see_obj`
  masking); the two TO_ALL aura lines deliver to the caster via `act_format` AND to
  the room via `act_to_room(caster.room, "$p …", caster, arg1=obj)`.
- **Tests**: `tests/integration/test_magic020_curse_object_pers.py` (caster + room
  observer both receive "A silver dagger glows with a malevolent aura."; already-evil
  → "A cursed blade is already filled with evil."). Existing curse test
  (`test_skills.py:540`, substring) stays green. Curse+skills suites 31/31.
- **MAGIC-016 cluster status**: armor/shield/bless/cures/curse all ✅ — **only
  `change_sex` remains** (literal `$s(?)` quirk).

### `MAGIC-021` — ✅ FIXED (change_sex replicates ROM's literal `$s(?)` quirk; cluster CLOSED)

- **Python**: `mud/skills/handlers.py:change_sex`.
- **ROM C**: `src/magic.c:1321` — `act("$N has already had $s(?) sex changed.", ch, NULL, victim, TO_CHAR)`.
- **Gap**: baked the victim name + "their" and dropped ROM's literal `$s(?)`. ROM's
  `$s` is the **caster's** possessive (a likely ROM bug — grammatically should be the
  victim's `$S` — which the author flagged with the literal "(?)"). Per "replicate
  ROM quirks exactly", we keep the bug verbatim.
- **Fix**: `act_format("$N has already had $s(?) sex changed.", recipient=caster,
  actor=caster, arg2=victim)` — `$N` = victim PERS (cap), `$s` = caster possessive,
  literal "(?)". A male caster changing an already-changed "a green goblin" → "A
  green goblin has already had his(?) sex changed." (the "his" is the *caster's*).
- **Tests**: `tests/integration/test_magic021_change_sex_quirk.py` (male caster +
  female NPC victim → caster's "his(?)"); inverted `test_skills_buffs.py:74`
  ("their"→"his(?)", made the caster explicitly male).
- **MAGIC-016 cluster: CLOSED** — armor, shield, bless, cures, curse, change_sex all
  ✅. The systematic spell-handler baked-name sweep is complete.

### `MAGIC-022` — ✅ FIXED (protection_evil/good messages use `$N` PERS short_descr)

- **Python**: `mud/skills/handlers.py:protection_evil`/`protection_good`.
- **ROM C**: `spell_protection_evil`/`_good` — `act("$N is already protected.", …)` + `act("$N is protected from evil/good.", …)`, TO_CHAR.
- **Gap**: 6 baked-name sites across the sibling pair. Protecting an NPC
  "goblin"/"a green goblin" showed "goblin is protected from evil." vs ROM "A green
  goblin is protected from evil."
- **Fix**: all six via `act_format("$N …", arg2=target)`. Had to add room setup to
  the two existing `test_skills_buffs.py` protection tests — they created
  caster/target with **no room**, so PERS's `can_see` returned "Someone"; adding a
  lit room resolves the name (this is a real test-setup gap the baked-name code
  masked).
- **Tests**: `tests/integration/test_magic022_protection_pers.py` (NPC →
  "A green goblin is protected from evil." / "… is already protected."). Buffs
  suite 27/27.
- **⚠️ NEW ENUMERATED BATCH filed** (in `MAGIC_C_AUDIT.md` MAGIC-022 row): the
  baked-name pattern is pervasive — ~15 MORE spell-handler sites remain
  (faerie_fire, disarm, fly, frenzy, giant_strength, haste, infravision, pass_door,
  fireproof, envenom, bless-object, …). Each needs its ROM `act()` code verified
  ($N/$E/$p/$S/literal) before the same `act_format` conversion. **Lesson:** when a
  grep reveals a class is pervasive, enumerate it in the tracker so the scope is
  durable — don't let "I fixed the ones I found" imply completeness.

### Re-verified faithful this session (recall-oracle, no change)

`do_quit` (connection-layer tear-down handled by the harness via `_quit_requested`)
and `do_train` (trainer-first gate, +10 hp/mana to perm/max/current, +1 stat,
`get_max_train` gate, all three TO_ROOM increase broadcasts, the big-stud/hot-babe/
wild-thing easter eggs) both confirmed ROM-faithful against source.

## ROM WAIT_STATE-site cross-check (this session's method)

Enumerated every `WAIT_STATE(ch, <value>)` site in the ROM `src/*.c` files and
cross-checked the Python equivalent. **Confirmed faithful (no change):**
`move_char` (1), `do_recall` (4), `do_shout` (12), `do_brandish`/`do_zap`
(2*PULSE_VIOLENCE), `do_berserk` (12 success / 36 fail), `do_kill`/`do_murder`
(PULSE_VIOLENCE), healer. **Fixed this session:** `do_order` (ORDER-002, was
missing), `do_save` (SAVE-001, was missing), `do_password` (PASSWORD-001, was
`=` not UMAX), `do_cast` (CAST-010, was flat 12 not per-spell beats). The
recurring tells: a `# not implemented yet` / `# Placeholder` stub, a plain `=`
assignment where ROM's macro is UMAX, or a flat constant where ROM reads a
per-entity field.

## Outstanding

- **do_pick / pick_lock duplication** (filed by PICK-001): the live `pick` command
  is `mud/commands/doors.py:do_pick` (inline reimplementation), but a second,
  fully-featured `mud/skills/handlers.py:pick_lock` (dict-returning, already calls
  check_improve, used by `tests/test_skill_pick_lock_rom_parity.py`) exists in
  parallel. They are not wired together — `do_pick` does not delegate. This is the
  same shape SNEAK-001/HIDE-001 reconciled (make the command delegate to the
  canonical handler). Next agent: consider collapsing `do_pick` onto
  `handlers.pick_lock` so the two paths can't drift again. Not a behavior bug today
  (PICK-001 closed the observable divergence), but a maintenance/drift risk.

## Next Steps

Cross-file invariants remains the active pass. Remaining candidate probes:

1. **Mob memory / hunt** — `src/fight.c` ATTACK_BACK + the hunt/track loop vs the
   Python AI tick (not yet probed).
2. **Position-transition edges** — `update_pos` / `stop_fighting` ordering across
   damage, sleep, rest, and death (cross-INV candidate).

Confirmed-faithful (do not re-probe without new evidence): weather/time fan-out,
`update_handler` pulse cadence (locked by `tests/test_game_loop_order.py` +
`tests/integration/test_weather_time.py`).
