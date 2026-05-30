# Cross-File Invariants — ROM 2.4b6 → Python Port

## Why this tracker exists

`ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` and the per-file `<FILE>_C_AUDIT.md`
documents verify **functions**: "does Python function X behave like ROM
function X?" That methodology is necessary but not sufficient. Three
serious bugs shipped this year against files marked ≥95% audited:

- **Duplicate combat-message delivery** (`comm.c` row says 95%): every
  combat message reached connected players TWICE because
  `_push_message` (engine.py) appended to the mailbox AND scheduled an
  async send, and `connection.py` drained the mailbox separately. Each
  function was individually fine; the *contract* between them was
  broken.
- **PC not in character_registry after WS login** (`save.c` row says
  100%): the audit pointed at `mud/persistence.py` (the JSON-pfile
  path), but production WS logins use `mud/account/account_manager.py`
  (the SQLAlchemy path), which never appended. Combat was one-way for
  every WS login.
- **Negative hp leaked into prompt** (`comm.c` row says 95%): the
  death path could render `<-15hp>` between `update_pos` setting
  `Position.DEAD` and `raw_kill` clamping to `max(1, hit)`. ROM's
  single-threaded loop forbids this; Python's async dispatch allowed
  it.

These are **invariants**, not function divergences. They live in the
spaces between modules — call chains, ordering relationships,
membership contracts. This tracker enumerates them, names them with
stable IDs (INV-NNN), and points each at an enforcement test.

## How to use this tracker

- When opening a new audit (`/rom-parity-audit`), check whether any
  invariant in this tracker touches the file under audit. If yes, run
  the enforcement test before claiming ≥95%.
- When closing a gap (`/rom-gap-closer`), if the fix touches code in a
  module other than the audit's "primary" Python file, add a line to
  the relevant invariant's "Touched by" column. This keeps the call
  chain visible.
- When a NEW invariant surfaces (root cause of a bug crosses files),
  add it here with the next free INV-NNN. Stable IDs forever — never
  renumber.
- Status values: ✅ ENFORCED (failing test exists, currently green),
  ⚠️ VERIFIED MANUALLY (read-only confirmation, no test), ❌ BROKEN
  (known regression).

## Invariants

| ID | Name | ROM mechanism | Python enforcement point | Test | Status |
|----|------|---------------|--------------------------|------|--------|
| INV-028 | LIGHT-SLOT-KEY-COHERENCE | `src/act_obj.c:1415-1422 wear_obj` dispatches `ITEM_LIGHT` **first** (before any wear-flag branch) into the single `WEAR_LIGHT` slot via `equip_char(ch, obj, WEAR_LIGHT)`; `do_hold`/`do_wield`/`do_wear` all alias `wear_obj`, so `hold torch` lands in WEAR_LIGHT too. Both consumers read that same slot: room-light accounting (`src/handler.c:1504-1507` char_from_room / `1571-1573` char_to_room via `get_eq_char(ch, WEAR_LIGHT)`) and the PC per-tick burnout decay (`src/update.c:721-730`, `--ch->in_room->light` + `extract_obj`). One slot constant, used consistently across equip, room-light tracking, and decay. | (a) `mud/commands/equipment.py:do_wear` now has an `item_type == ItemType.LIGHT` branch (before the HOLD branch, mirroring ROM dispatch order) that equips into `int(WearLocation.LIGHT)` with the "lights $p and holds it" messages; the dead LIGHT special-case inside the HOLD branch was removed. `do_hold` aliases `do_wear`. (b) `mud/models/room.py:_has_lit_light_source` reads the LIGHT slot tolerating both `int(WearLocation.LIGHT)` (fresh equip) and the str `"0"` (post JSON save/reload). (c) `mud/game_loop.py:_find_equipped_light` matches `"light"`, the IntEnum/int LIGHT key, AND a numeric str equal to LIGHT (reload form). **Followup — CLOSED in 2.9.87 via equipment-key canonicalization.** `Character.equipment` is now keyed strictly by `int(WearLocation.X)` on every path: `Character.equip_object` runs its slot arg through the new `mud.models.constants.canonical_wear_slot` (int / numeric-str / legacy name → int), the JSON restore in `from_orm` coerces the reloaded str key back to int, and `mud/db/serializers.py:_slot_to_wear_loc` accepts the int slot. The per-reader LIGHT shims added here (room.py str-"0" fallback, game_loop.py "light"-name match) were REMOVED — readers now use the int key only. Two real bugs that the broader inconsistency was hiding were fixed at the same time: `give_school_outfit`'s lit war banner (equipped via the string `"light"`) was uncounted in room lighting, and a shield worn via `do_wear` (int key 11) was invisible to the combat shield check (`engine._has_shield_equipped` read the string `"shield"`). Convergence is locked by `tests/test_equipment_key_convention.py` (grep-guard banning string-literal equipment access in `mud/`) and `tests/integration/test_equip_key_canonical.py`. No new INV row (tracker over budget); see AGENTS.md "Equipment lookup". Touched by: `mud/models/character.py:equip_object`/`from_orm` restore, `mud/models/constants.py:canonical_wear_slot`, `mud/combat/engine.py` (wield+shield readers), `mud/commands/inventory.py:give_school_outfit`, `mud/skills/handlers.py` (floating-disc reader + `portal`/`nexus` HOLD warp-stone lookup), `mud/combat/death.py:_is_floating_slot`, `mud/db/serializers.py:_slot_to_wear_loc`, `mud/commands/compare.py:_find_equipped_match` (also fixed the latent `char.equipped` → `char.equipment` bug). Touched by: `mud/commands/equipment.py:do_wear`/`do_hold`, `mud/models/room.py:_has_lit_light_source`, `mud/game_loop.py:_find_equipped_light`/`_decay_worn_light`. | `tests/integration/test_inv028_light_slot_key_coherence.py` | ✅ ENFORCED (2.9.85) |
| INV-001 | SINGLE-DELIVERY | `src/comm.c:write_to_buffer` writes once per message; ROM commands (`do_kill`, …) write straight to the descriptor via `act()`/`send_to_char` and return void — there is no "return value" channel | `mud/combat/engine.py:_push_message` returns after async send when `connection` exists. **Commands MUST NOT return a line they also push:** the connection loop (`mud/net/connection.py:1980-2000`) sends a command's return value AND drains `char.messages`, so any line in both channels double-delivers to a connected PC. `do_kill` now returns `""` and delivers all combat output via `_push_message` (FIGHT-020); nearly every other `multi_hit` caller (`do_murder`, `violence_tick`, `assist`, aggressive AI, `spec_funs`) already discards its return. | `tests/integration/test_message_delivery_no_duplicate.py` (push channel single); `tests/integration/test_kill_command_single_delivery.py` (FIGHT-020 — command return must not duplicate the push, fatal + non-fatal); `tests/integration/test_broadcast_room_single_delivery.py` (broadcast_room/broadcast_global single delivery to connected PCs + mailbox fallback). Touched by: `mud/commands/combat.py:do_kill`, `mud/net/protocol.py:broadcast_room`/`broadcast_global`, `mud/skills/handlers.py:shield`/`sanctuary`/`blindness`/`weaken` (MAGIC-003, 2.11.24 — affect-spell victim/room lines moved off `char.messages.append` onto `_send_to_char`; test `tests/integration/test_magic_003_affect_message_channel.py`), `mud/skills/handlers.py:rescue` + `mud/commands/combat.py:do_rescue` (FIGHT-029, 2.11.25 — three rescue legs onto `_send_to_char`, command returns `""`, fail-path append dropped; test `tests/integration/test_rescue_single_delivery.py`). **(a) `broadcast_room`/`broadcast_global` — ✅ FIXED (2.11.6):** they appended to BOTH the async `send_to_char` task AND `char.messages`, so a connected PC in the room received every room broadcast (death/position-change/says routed through them) twice; now connection-XOR-mailbox like `push_message` (mailbox fallback preserved for disconnected chars / tests). Surfaced by the FIGHT-020 death-path test (`{RVictim is DEAD!!{x` ×2, `hits the ground … DEAD.` ×2). **(b) `do_surrender` — ✅ FIXED (2.11.7):** the NPC-ignores-surrender branch did `attack_messages = multi_hit(opponent, char)` then returned them, so the surrendering PC received the TO_VICT push AND `do_surrender`'s returned attacker-perspective ("You hit …") line — a return-value double-send + wrong-perspective leak. ROM `src/fight.c:3239-3240` calls `multi_hit(mob, ch, TYPE_UNDEFINED)` void; now the return is discarded like `do_kill`. Test: `tests/integration/test_surrender_single_delivery.py`. **(c) `do_rescue` — ✅ FIXED (FIGHT-029, 2.11.25):** `rescue()` (`mud/skills/handlers.py`) appended the rescuer's `char_msg` to `caster.messages` AND `do_rescue` returned it, so a connected PC rescuer got "You rescue X!" twice (the `do_kill`/`do_surrender` shape); the victim/room legs used the raw mailbox (MAGIC-003 wrong-channel). Now `rescue()` delivers all three legs (TO_CHAR/TO_VICT/TO_NOTVICT, `src/fight.c:3089-3091`) via `_send_to_char` and `do_rescue` returns `""`; the fail-path `"You fail the rescue."` mailbox append was likewise dropped (return-channel only). Test: `tests/integration/test_rescue_single_delivery.py` (rescuer count-once + victim/bystander push-present + mailbox-empty — a pure count test false-greens on the vict/room legs since those are wrong-channel, not duplicated). **(d) `"You are still recovering."` cross-command sweep — ✅ FIXED (2.11.27):** the wait-state guard in 7 `mud/commands/combat.py` commands (`do_kick`, `do_rescue`, `do_backstab`, `do_bash`, `do_berserk`, `do_flee`, `do_cast`) did `char.messages.append("You are still recovering.")` AND `return "You are still recovering."` → double-delivery to a connected PC (the connection loop sends the return AND drains the mailbox; the FIGHT-029 fail-path shape). Not a ROM line (ROM gates wait at the interpreter level, silent), so the message is kept but delivered once — fix dropped the append, kept the return at all 7 sites. **`mud/skills/registry.py:163` was DELIBERATELY EXCLUDED (not a violation):** it appends the line to the mailbox then `raise`s `ValueError("still recovering")` — it does **not** return the line, has **no production callers** (only tests invoke `SkillRegistry.use`), and the connection loop sends a generic error string on any exception (never the exception text). So its append is a single mailbox delivery in a test-only path, not a double; the "drop append, keep return" fix structurally does not apply (there is no return to keep), and `tests/test_skills.py:225` asserts that mailbox delivery. Do not re-flag registry.py on a future `grep "still recovering"`. Enforcement: `tests/integration/test_still_recovering_single_delivery.py` — a grep-guard locking all 7 combat.py sites and any future re-addition (the AGENTS.md `test_rng_determinism.py`/`test_equipment_key_convention.py` idiom) plus a behavioral connected-PC single-delivery test through `do_kick`. Surfaced while closing FIGHT-029 via `grep "still recovering"`. **(e) `do_buy` pet-shop branch (`_handle_pet_shop_purchase`) — ✅ FIXED (2.11.29):** the success line `"Enjoy your pet."` was `char.messages.append(...)` AND returned by `do_buy`, so a connected PC buying a pet saw it **twice** (the `do_kill` / INV-001 (d) shape — the connection loop sends the return AND drains the mailbox). ROM `do_buy` (`src/act_obj.c:2635`) does `send_to_char("Enjoy your pet.\n\r", ch)` once and returns void. Fixed by dropping the mailbox append and keeping the return (the INV-001 (d) recipe). Test `tests/integration/test_pet_buy_single_delivery.py` (behavioral connected-PC single-delivery through `do_buy` — fail-first showed `['Enjoy your pet.', 'companion pet now follows you.', 'Enjoy your pet.']`, 2×). `tests/test_shops.py:test_pet_shop_purchase_creates_charmed_pet` realigned (mailbox no longer carries the line; the return is the sole delivery). **Lesser wrong-channel cousins in the same function (noted, NOT fixed by (e)):** the haggle line `"You haggle the price down to N coins."` (ROM `src/act_obj.c:2606-2607` `send_to_char`, immediate) and the `add_follower` `"… now follows you."` line are mailbox-only — wrong-channel (late) for a connected PC rather than doubled; the haggle wrong-channel also spans the item-buy/sell branches (broader, separate — not folded in). Surfaced 2026-05-29 by the advisor while closing SHOP-PET-002 (which rewrote this function). | ✅ ENFORCED for double-delivery (a–e all closed: `do_kill` + `broadcast_room`/`broadcast_global` + `do_surrender` + `do_rescue`/FIGHT-029 + "still recovering" (d)/2.11.27 + pet-buy "Enjoy your pet." (e)/2.11.29). ⚠️ **One wrong-channel cousin OPEN/tracked** (same family per the MAGIC-003 / `do_rescue` (c) precedent, NOT a double-delivery): the pet-shop haggle line `"You haggle the price down to N coins."` (ROM `src/act_obj.c:2606-2607` `send_to_char`, immediate) and the `add_follower` "… now follows you." line are mailbox-only → late for a connected PC. The haggle wrong-channel also spans the `do_buy`/`do_sell` item branches — a shop-wide MAGIC-003-style channel pass, not yet scoped. |
| INV-002 | PROMPT-CLAMP | `src/comm.c:1420ff bust_a_prompt` runs after `src/fight.c:1718 raw_kill` clamps `hit >= 1` (single-threaded) | `mud/utils/prompt.py` clamps display to `max(0, hit)` at both render sites | `tests/test_prompt_clamps_hp.py` | ✅ ENFORCED |
| INV-003 | REGISTRY-MEMBERSHIP | `src/save.c:fread_char` appends to `char_list`; pulse handlers iterate it | Every `load_character` path appends to `mud.models.character.character_registry` | `tests/integration/test_character_creation_runtime.py::TestCharacterRegistryRegistration` | ✅ ENFORCED |
| INV-004 | PC-CONNECTION-SURVIVES-DEATH | `src/handler.c:2103-2187 extract_char(ch, FALSE)` keeps PC descriptor open | `mud/combat/death.py:raw_kill` does not touch `char.connection`; PC stays in registry | `tests/integration/test_pc_death_keeps_connection.py` | ✅ ENFORCED |
| INV-005 | SAME-ROOM-COMBAT-ONLY | `src/fight.c:violence_update` skips if `ch->in_room != victim->in_room` | `mud/game_loop.py:violence_tick` checks `attacker.room == victim.room` before `multi_hit` | `tests/integration/test_inv005_same_room_combat.py` | ✅ ENFORCED |
| INV-006 | FIGHTING-POINTER-COHERENCE | `src/fight.c:stop_fighting(victim, TRUE)` sweeps `char_list`, clears every `fch->fighting == victim` | `mud/combat/engine.py:stop_fighting(ch, both=True)` iterates `character_registry` | `tests/integration/test_inv006_fighting_pointer_coherence.py` | ✅ ENFORCED |
| INV-007 | RNG-DETERMINISM | `src/db.c init_mm` Mitchell-Moore RNG is the only source of combat/affect rolls | All `mud/combat/`, `mud/skills/`, `mud/spells/` use `mud.math.rng_mm.number_*`; never `random.*` | `tests/test_rng_determinism.py` | ✅ ENFORCED |
| INV-008 | DUAL-LOAD-CHARACTER-COHERENCE | (Python-only) Single canonical store for player state; no dual JSON-pfile / DB-row split | `mud/db/models.py:Character` is canonical (39 + base columns); `mud/account/account_manager.py:save_character` calls `save_character_to_db` (UPDATE), `load_character` queries the DB and runs `Character.from_orm`; serialization helpers live in `mud/db/serializers.py`; time-info persistence in `mud/world/time_persistence.py`; `mud/persistence.py` deleted (2.8.3) | `tests/integration/test_inv008_persistence_coherence.py` + `tests/integration/test_db_canonical_round_trip.py` | ✅ ENFORCED |
| INV-009 | REGISTRY-DISCONNECT-CLEANUP | `src/comm.c:close_socket` + `src/nanny.c:do_quit` ensure char_list has at most one entry per player name at any time; reconnects rebind via `check_reconnect` rather than appending duplicates | (a) `mud/account/account_manager.py:load_character` dedupes by `name` before appending — drops any prior `character_registry` entry with the same name (e.g. the level=0 bare-row Character loaded during the nanny name/password phase) before adding the freshly-loaded one. (b) `mud/net/connection.py` disconnect cleanup (websocket + telnet `finally` blocks) removes the Character from `character_registry` on non-forced disconnect, matching the `save + char_from_room + release_account` quit semantics already in place. Forced disconnects (descriptor takeover via `_disconnect_session`) skip removal — the Character transfers to the new descriptor. | `tests/integration/test_inv009_registry_disconnect_cleanup.py` | ✅ ENFORCED |
| INV-010 | ROOM-PEOPLE-COHERENCE | **Consolidated 2.9.41** (was INV-010 ROOM-PEOPLE-COHERENCE + INV-023 AREA-NPLAYER-COHERENCE — sub-contracts under the same `char_from_room`/`char_to_room` umbrella). **Room-people side**: `src/handler.c:1497-1573 char_from_room / char_to_room` are the only mutation paths; bidirectional contract — every `ch->in_room == R` lives in `R->people`, every entry in `R->people` has `ch->in_room == R`. ROM also relies on a single canonical `room_index_hash` lookup table (`src/db.c:get_room_index`). **Area-counter side**: those same two routines also own area-level accounting: `src/handler.c:1501-1502` decrements `ch->in_room->area->nplayer` when `!IS_NPC(ch)`; `src/handler.c:1561-1568` increments it on the destination side, clears `area->empty`, and resets `area->age` on first PC arrival. `area->nplayer` is load-bearing — `src/db.c:1617-1630, 1773, 1808` use it to gate area resets, mark areas empty, and tick area age. The two halves share one invariant: every PC movement must funnel through `add_character`/`remove_character`, never direct list mutation; bypass leaks both bidirectional coherence AND area counters. | **Room-people coherence**: (a) `mud/models/room.py:Room.add_character` / `Room.remove_character` keep the bidirectional state synchronized. (b) `mud/models/room.py:char_to_room` wraps `add_character` with a NULL → temple fallback. (c) `mud/models/room.py` no longer declares a second `room_registry` dict; it re-imports the canonical `mud.registry.room_registry`, so the temple fallback and `mud/game_loop.py:525` limbo lookup read from the world-loaded registry rather than a perpetually empty one (fixed in 2.8.78). **Area-counter coherence**: (d) `Room.add_character` (lines 140-155) and `Room.remove_character` (lines 157-173) own `area.nplayer` increment/decrement gated on `not is_npc`, plus `empty=False`/`age=0` reset on first arrival. (e) `mud/commands/session.py:do_recall` (lines 392-399) routes through `old_room.remove_character(ch)` and `recall_room.add_character(ch)` (fixed in 2.9.37 — previously mutated `room.people` directly via `.remove`/`.append`, bypassing the counter so cross-area recall left both areas with skewed `nplayer`). (f) All other PC-movement sites (movement.py do_move, transfer commands, etc.) already route through `add_character`/`remove_character`. Direct `room.people` list manipulation in NPC-only paths (`mud/mob_cmds.py:267, 330, 686`, `mud/spec_funs.py:214-217 mayor`, `mud/spawning/templates.py:438-439 MobInstance.move_to_room`) is intentional — those entities are NPCs and the counter excludes NPCs by ROM contract. Touched by: `mud/spec_funs.py` (mayor patrol), `mud/spawning/templates.py:MobInstance.move_to_room`, `mud/commands/session.py:do_recall`, `mud/commands/imm_load.py`, `mud/commands/imm_search.py`, `mud/commands/imm_commands.py:_char_from_room/_char_to_room`. | `tests/integration/test_inv010_room_people_coherence.py` + `tests/integration/test_inv023_area_nplayer_coherence.py` | ✅ ENFORCED |
| INV-011 | CARRY-WEIGHT-COHERENCE | `src/handler.c:1626 obj_to_char` / `1642 obj_from_char` keep `ch->carry_weight` and `ch->carry_number` in lockstep with `ch->carrying`. `extract_obj` (`src/handler.c:2051,2058-2059`) routes through `obj_from_char` so the counters never drift. | (a) `Character.add_object` / `Character.equip_object` / `Character.remove_object` (mud/models/character.py:542-566) call `_recalculate_carry_weight` and adjust `carry_number`. (b) `mud/game_loop.py:_remove_from_character` (used by `_extract_obj` → carrier branch and by corpse decay) also re-derives `carry_weight` via `_recalculate_carry_weight` and decrements `carry_number` by the obj's slot cost (fixed in 2.8.79 — previously dropped the obj from inventory/equipment without touching the cached counters, so every extract on a carried object skewed encumbrance upward). Touched by: `mud/game_loop.py:_extract_obj` and `_decay_carried_light`, `mud/mob_cmds.py:1095-1110` (mpoload-style cleanup), `mud/combat/engine.py:991` (corpse extract), `mud/mob_cmds.py:do_mpoload` inventory branch (fixed in 2.9.4 — previously appended directly to `ch.inventory` without going through `add_object`, drifting `carry_weight` / `carry_number` on every MOBprog `mob oload <vnum>`). | `tests/integration/test_inv011_carry_weight_coherence.py` | ✅ ENFORCED |
| INV-013 | OBJECT-LOCATION-COHERENCE | `src/handler.c:1626 obj_to_char`, `1953 obj_to_room`, `1968 obj_to_obj` keep `in_room`, `carried_by`, `in_obj` mutually exclusive — every set on one clears the other two. `obj_from_room` / `obj_from_char` / `obj_from_obj` each clear exactly one field. ROM has no "location" concept distinct from these three. | (a) `Object.location` (mud/models/object.py) is no longer a stored field; it is a property dispatching to `in_room` / `carried_by` / `in_obj` based on the target type (Room → in_room, Character → carried_by, Object → in_obj, None → clear all three). Reads return whichever ROM field is non-None. (b) Bug surfaced during conversion: `MobInstance.add_to_inventory` (mud/spawning/templates.py:442) set `obj.carried_by = mob` then `obj.location = None`, which under the new dispatch cleared carried_by — the `obj.location = None` line was deleted. (c) Bug surfaced during conversion: `make_corpse` (mud/combat/death.py:441) set `money_obj.location = None` while appending to `corpse.contained_items`; per ROM's obj_to_obj, money inside a corpse must have `in_obj = corpse` — fixed to `money_obj.location = corpse`. (d) `mud/handler.py:638` defensive bridge `getattr(obj, "in_room", None) or getattr(obj, "location", None)` becomes redundant — left in place for resilience, harmless. (e) `mud/models/character.py:Character.add_object` now sets `obj.location = self` after the inventory append (fixed in 2.9.4 — previously updated carry counters but left the canonical `carried_by` field unset, so every direct `add_object` caller silently produced an inventory item with no carrier back-pointer). (f) `Character.equip_object` sets `obj.carried_by = self`, and `Character.remove_object` clears it (fixed in 2.9.5 — previously equip left it at whatever the inventory path had set, and remove left a stale back-pointer to the former carrier; ROM `equip_char` keeps the carrier set, `obj_from_char` clears it atomically). Touched by: every Object.location read/write across mud/ — semantically converged through the property, no caller sweep required. | `tests/integration/test_inv013_object_location_coherence.py` | ✅ ENFORCED |
| INV-012 | OBJECT-LIST-CANONICAL | `src/db.c:create_object` appends every new `OBJ_DATA` to the global `object_list`; `src/handler.c:2051 extract_obj` removes (recursively for contents via lines 2063-2067). ROM has ONE struct, ONE list, four exclusive containers (`in_room`, `carried_by`, `in_obj`, equipped via `wear_loc`). | (a) `mud/models/object.py:Object` is the only runtime class. `mud/models/obj.py:ObjectData` deleted in 2.9.0; the dual-class divergence (parallel to INV-008) is closed. (b) ROM-named container fields `in_room`, `in_obj`, `carried_by` live on `Object` as real dataclass fields (compare=False to avoid graph-walking `__eq__`). `pIndexData` and `contains` are read+write/read-only `@property` aliases of `prototype` and `contained_items`. (c) `mud/spawning/obj_spawner.py:spawn_object` appends every new instance to `mud.models.obj.object_registry: list[Object]` before returning. `mud/game_loop.py:_extract_obj` removes (recursively via `obj.contained_items`). `tests/conftest.py` autouse fixture snapshots-clears-restores the registry around every test to prevent cross-test leakage. Touched by: `mud/skills/handlers.py` (3 single-arm + 9 tuple-filter isinstance collapses), `mud/game_loop.py` (17 helper retypings + 4 dual-shape fallback deletions), `mud/handler.py` (3 affect-helper retypings), `mud/music/__init__.py`, `mud/ai/__init__.py`, `mud/mob_cmds.py`, 9 test files (35 fixture migrations). | `tests/integration/test_inv012_object_list_canonical.py` | ✅ ENFORCED |
| INV-026 | VIOLENCE-TRIGGER-DISPATCH-SCOPE | `src/fight.c:60-99 violence_update` is the ONLY ROM site that fires `TRIG_FIGHT` (`mp_percent_trigger(ch, victim, ..., TRIG_FIGHT)`) and `TRIG_HPCNT` (`mp_hprct_trigger`). Per-iteration sequence: `multi_hit(ch, victim, TYPE_UNDEFINED)` → `if ((victim = ch->fighting) == NULL) continue;` (skip if victim died) → `check_assist(ch, victim)` → `if (IS_NPC(ch))` then HPCNT/FIGHT. Three-part contract: (i) dispatch lives ONLY in the violence pulse, never inside `multi_hit` itself, so non-violence callers (`do_kill`, `assist`, `spec_funs`, `mob_cmds`) do not provoke the triggers; (ii) the victim-still-fighting guard skips the dispatch when the round's killing blow landed; (iii) attacker-side guard `IS_NPC(ch)` — PC attackers never fire mob-side triggers. | (a) `mud/game_loop.py:violence_tick` (lines 1322-1348) now owns the dispatch: after `multi_hit(ch, victim, dt=None)` returns, if `getattr(ch, "is_npc", False) and getattr(ch, "fighting", None) is victim`, fires `mobprog.mp_fight_trigger(ch, victim)` then `mobprog.mp_hprct_trigger(ch, victim)`. The `attacker.fighting is victim` re-read (not the loop-local `victim` parameter) mirrors ROM's `(victim = ch->fighting) == NULL` re-fetch — `stop_fighting` during multi_hit clears `ch->fighting`, so the freshly-read attribute is the load-bearing check. (b) `mud/combat/engine.py:multi_hit` (line 360 area) — the previous shallow HPCNT-001 enforcement point — no longer dispatches; the dispatch was lifted out so the trigger is invisible to non-violence callers. (c) `mud/combat/assist.py:multi_hit` (3 sites: assist-mob joining combat at lines 72/85/150), `mud/spec_funs.py:873` (spec_cast_* paths), `mud/mob_cmds.py:1054, 1075` (mob `kill` directive), and any future caller of `multi_hit` no longer fire TRIG_FIGHT/TRIG_HPCNT — matches ROM where those C callers also do not fire them. Pre-INV-026 every assist-mob join, every spec_fun attack, and every `mob kill` call dispatched TRIG_FIGHT/TRIG_HPCNT on the attacker, contradicting ROM. **Adjacent check_assist misplacement closed (2.9.44)**: `check_assist` was lifted out of `mud/combat/engine.py:multi_hit` and into `mud/game_loop.py:violence_tick` before the NPC trigger dispatch, mirroring ROM `src/fight.c:90` ordering (`check_assist` → IS_NPC → TRIG_FIGHT/TRIG_HPCNT). Same misplacement shape as the original INV-026 lift; folded under this row since it shares the violence_update contract (no new INV-NNN row). The violence_tick now re-reads `attacker.fighting is victim` twice — once after `multi_hit` (victim-died guard, ROM `src/fight.c:84-85`), once after `check_assist` (helper-landed-killing-blow guard). Pre-2.9.44, every direct caller of `multi_hit` (`mud/combat/assist.py` recursive assist round, `mud/spec_funs.py` spec_cast paths, `mud/mob_cmds.py` mob `kill` directive) provoked another assist round, contradicting ROM. Touched by: `mud/game_loop.py:violence_tick`, `mud/combat/engine.py:multi_hit`, `mud/combat/assist.py:check_assist`. | `tests/integration/test_inv026_violence_trigger_dispatch.py` + `tests/integration/test_check_assist_dispatch_scope.py` + `tests/integration/test_hpcnt_once_per_pulse.py::test_hpcnt_fires_exactly_once_per_violence_tick` | ✅ ENFORCED |
| INV-025 | MOBPROG-ACT-TRIGGER-DISPATCH | `src/comm.c:2384-2385` — inside `act()` itself, after the per-recipient buffer is formatted, every NPC `to` (`to->desc == NULL` or `to->desc->connected != CON_PLAYING`) receives `mp_act_trigger(buf, to, ch, arg1, arg2, TRIG_ACT)` provided the global `bool MOBtrigger` (`src/comm.c:311`) is TRUE. ROM toggles `MOBtrigger = FALSE` around recursive paths (`src/act_obj.c:832-836 do_give`, `src/mob_cmds.c:333-335 do_at`) so a TRIG_ACT response that itself calls `act()` does not re-fire on the same mob. Two-level contract: (i) every act()-driven broadcast must dispatch TRIG_ACT to NPC recipients in the room; (ii) the MOBtrigger recursion guard must suppress that dispatch when callers explicitly opt out. | (a) `mud/mobprog.py` exposes a module-level `MOBtrigger: bool = True` flag and a `disable_mobtrigger()` context manager (lines 19-46) — the Python port of ROM's `MOBtrigger = FALSE; act(...); MOBtrigger = TRUE;` pattern. Nesting is safe (previous value is restored, not unconditionally set TRUE) so future recursive paths can stack the guard without leaking. (b) `mud/mobprog.py:mp_act_trigger_room(message, room, ch, *, arg1, arg2, exclude)` (the per-room dispatcher) iterates `room.people`, skips PCs / `ch` / `exclude`, fires `mp_act_trigger` per NPC, and short-circuits on `MOBtrigger == False`. (c) `mud/commands/communication.py:do_emote` — the canonical ROM TRIG_ACT producer (`act("$n $T", ch, NULL, argument, TO_ROOM)` at `src/act_comm.c:1091`) — now calls `mp_act_trigger_room(args, char.room, char)` after the per-listener fan-out. Pre-INV-025, every TRIG_ACT mobprog responding to PC emotes silently no-opped because Python only routed speech to mobprog. **Follow-up wiring sweep** (deferred): remaining act()-style broadcast sites (`broadcast_room`, `_push_message`, position-transition broadcasts in `mud/combat/engine.py`, give/wear/drop/sacrifice in `mud/commands/`) should also fan into `mp_act_trigger_room` when they correspond to a ROM `act()` call. The contract is locked at the emote callsite; the sweep extends coverage but cannot regress the contract. Touched by: `mud/mobprog.py:MOBtrigger`, `mud/mobprog.py:disable_mobtrigger`, `mud/mobprog.py:mp_act_trigger_room`, `mud/commands/communication.py:do_emote`. | `tests/integration/test_inv025_mobprog_act_trigger_dispatch.py` | ✅ ENFORCED |
| INV-024 | CONTAINER-CLOSED-VISIBILITY | `src/act_obj.c:291-295 do_get` and `:384-388 do_put` short-circuit with "The $d is closed." when the target ITEM_CONTAINER has `CONT_CLOSED` set on `value[1]`. `src/act_info.c:1160-1162` (`do_look "in <container>"`) emits "It is closed." and returns. `src/act_info.c:1320-1386 do_examine` delegates to `do_look "in <name>"` for ITEM_CONTAINER / ITEM_CORPSE_NPC / ITEM_CORPSE_PC, inheriting the gate transitively. ROM reads `container->value[1]` off the OBJ_DATA instance — open/close mutates the per-instance value array, not the prototype. Four-surface contract: get-from, put-into, look-in, examine; any unguarded surface lets a player read or move items through a closed lid. | (a) `mud/commands/inventory.py:do_get` (lines 512-518) gates the transfer; **fixed in 2.9.38** — previously read `container.prototype.value[1]` instead of `container.value[1]`, so `get all <chest>` bypassed the gate whenever the instance was closed but the prototype default was open (which is the production loader's default for all container prototypes). Surfaced by INV-024's regression test on a freshly-spawned instance. (b) `mud/commands/obj_manipulation.py:do_put` (lines 103-106) correctly reads `container.value`. (c) `mud/world/look.py:_look_at_object` (lines 323-326) correctly reads `obj.value` via `look in <container>`. (d) `mud/commands/info_extended.py:do_examine` delegates to `do_look "in <name>"` for ITEM_CONTAINER / ITEM_CORPSE_NPC / ITEM_CORPSE_PC, inheriting the gate. Touched by: `mud/commands/inventory.py:do_get`, `mud/commands/obj_manipulation.py:do_put`, `mud/world/look.py:_look_at_object`, `mud/commands/info_extended.py:do_examine`. | `tests/integration/test_inv024_container_closed_visibility.py` | ✅ ENFORCED |
| INV-022 | EQUIP-APPLIES-OBJECT-AFFECTS | `src/handler.c:1754-1797 equip_char` is the canonical equip path: after setting `obj->wear_loc` it walks `obj->affected` (and the unenchanted `obj->pIndexData->affected`) and calls `affect_modify(ch, paf, TRUE)` for every affect — applying stat/AC/hitroll/damroll deltas and bitvector grants in lockstep with the equip. `unequip_char` (`src/handler.c:1804-1877`) is the inverse: `affect_modify(ch, paf, FALSE)` per affect, then clears `wear_loc`. Three-module contract: command surface must route through `equip_char`/`unequip_char`; those routines must walk both the per-instance and prototype affected lists; `affect_modify` must be the per-affect apply/strip primitive. | (a) `mud/handler.py:equip_char` (lines 159-214) and `unequip_char` (lines 217+) implement the ROM ladder — `affect_modify(ch, paf, True/False)` on every entry that isn't `APPLY_SPELL_AFFECT` (which routes through the spell-effects path), AC delta via `apply_ac`, plus the LIGHT-room counter side-effect. (b) `mud/handler.py:affect_modify` (lines 62+) is the canonical per-affect primitive. (c) `mud/commands/equipment.py` (do_wear/do_remove/do_wield/do_hold at lines 68, 197, 272, 345, 441) routes through `equip_char`/`unequip_char` — verified by grep over `mud/commands/`. (d) The two `Character.equip_object` direct call sites in `mud/commands/inventory.py:159,172` are inside `give_school_outfit` and operate on items whose `obj.affected` is empty by design (school banner/vest/sword/shield are vanilla starter gear). If a future school-outfit item gains an affect, that call site must move to `equip_char` — INV-022's test catches the regression on the production path either way. Currently enforced by construction; pinned with regression test that equips a +N hitroll/damroll affect and verifies the delta lands on `ch.hitroll`/`ch.damroll` and reverses cleanly on unequip. Touched by: `mud/handler.py:equip_char`, `:unequip_char`, `:affect_modify`, every command in `mud/commands/equipment.py`. | `tests/integration/test_inv022_equip_applies_object_affects.py` | ✅ ENFORCED |
| INV-020 | EXTRACT-CHAR-CLEANUP-CHAIN | **Expanded 2.9.46** (was GROUP-LEADER-COHERENCE-ON-RAW-KILL — narrow to raw_kill). ROM `src/handler.c:2103-2180 extract_char` is the canonical PC-removal chokepoint with a 4-step cleanup chain: (i) `nuke_pets(ch)` — `src/act_comm.c:1640-1654` dismisses the charmed pet via `stop_follower(pet) → act("$N slowly fades away.") → extract_char(pet, TRUE)`; (ii) `ch->pet = NULL`; (iii) `if (fPull) die_follower(ch)` — `src/act_comm.c:1658-1680` clears ch's own master, resets ch->leader, and walks `char_list` resetting every `fch->leader == ch` to `fch->leader = fch` (NOT NULL — `src/handler.c:2018 is_same_group` would still equate two former members via their dangling pointer at the corpse if leader were nulled) and calling `stop_follower(fch)` for every `fch->master == ch`; (iv) `stop_fighting(ch, TRUE)`. Every PC-extract trigger funnels through `extract_char(ch, TRUE)`: `raw_kill` (`src/fight.c:1718` — original INV-020 leg), `do_quit` (`src/act_comm.c:1499`), `do_pull` immortal commands, mob-script extract. Three-module contract: the extract funnel must invoke pet-nuke AND follower-cleanup before unlinking from `char_list`/room, the cleanup must walk the registry, and `is_same_group` must consult the leader pointer. | (a) `mud/combat/death.py:raw_kill` calls `die_follower(victim)` at line 562 BEFORE `character_registry.remove(victim)` at line 575 (NPC path). `_nuke_pets(victim)` is invoked too. (b) `mud/characters/follow.py:die_follower` (lines 80-99) iterates `character_registry` and runs the two branches: `fch.master is char ⇒ stop_follower(fch)` and `fch.leader is char ⇒ fch.leader = fch`. (c) `mud/commands/group_commands.py:is_same_group` compares `leader or self` pointers, so the leader-self reset is what closes the dangling-pointer hazard. (d) `mud/mob_cmds.py:_extract_character` (lines 226-296) is the canonical Python chokepoint — calls `_nuke_pets(victim, room=...)` then `if fPull: die_follower(victim)` then `stop_fighting(victim, both=True)` then inventory extract then room/registry removal, mirroring ROM line-by-line. **(e) New 2.9.46**: `mud/game_loop.py:_auto_quit_character` (void-quit auto-pull path) calls `_nuke_pets + character.pet = None + die_follower` before the room/registry cleanup. **(f) New 2.9.47**: `mud/net/connection.py:_disconnect_extract_cleanup` (helper extracted from the anonymous telnet+websocket disconnect `finally`-blocks at lines 1989+ and 2263+) wires the same chain into the socket-close path, gated on `not forced_disconnect` because `_disconnect_session` transfers the live Character to a new descriptor (Character is not being extracted there). All four PC-extract triggers (raw_kill, do_quit-derived void-quit, do_pull-derived `_extract_character`, socket disconnect) now funnel through `_nuke_pets + die_follower`. Touched by: `mud/combat/death.py:raw_kill + _nuke_pets`, `mud/characters/follow.py:die_follower + stop_follower`, `mud/commands/group_commands.py:is_same_group`, `mud/mob_cmds.py:_extract_character`, `mud/game_loop.py:_auto_quit_character`, `mud/net/connection.py:_disconnect_extract_cleanup`. | `tests/integration/test_inv020_group_leader_coherence_on_raw_kill.py` + `tests/integration/test_die_follower_leader_chain.py` (raw_kill leg) + `tests/integration/test_inv020_extract_quit_cleanup.py` (void-quit leg: `test_void_quit_nukes_pets` + `test_void_quit_calls_die_follower`; disconnect leg: `test_disconnect_nukes_pets` + `test_disconnect_calls_die_follower`) | ✅ ENFORCED |
| INV-019 | POSITION-PROMOTION-ON-HEAL | `src/fight.c:1380-1387 update_pos` — when `victim->hit > 0`, if `position <= POS_STUNNED` the victim is promoted to `POS_STANDING` **silently** (no `act()` call, no self-line). This is the upward counterpart of INV-016's downward broadcast. ROM calls `update_pos` from every direct-heal spell (`src/magic.c:1632, 1675, 1716, 3116` — `spell_cure_light/serious/critical/heal`), from `stop_fighting` (`src/fight.c:1448`), and from the regen tick when a STUNNED char's `hit_gain` lifts hp above 0 (`src/update.c:714-715`). Three-module contract: heal handlers, the regen pipeline, and `update_pos` itself must agree that hp > 0 + position <= STUNNED ⇒ STANDING, with no broadcast. | (a) `mud/combat/engine.py:update_pos` (lines 677-697) implements the ROM ladder byte-for-byte: `hit > 0 and position <= STUNNED → STANDING` (silent), NPC death at hit<1, PC death/MORTAL/INCAP/STUNNED thresholds below 0. (b) `mud/game_loop.py:char_update` (line 713-716) regen pipeline runs `_apply_regeneration(character)` for `position >= STUNNED`, then `update_pos(character)` only when `position == STUNNED` — the load-bearing order. (c) `mud/skills/handlers.py` heal sites (`cure_light` 2577, `cure_critical` 2522, `cure_serious` 2633, `heal` 4861) all call `update_pos(target)` after `target.hit += heal` — matches ROM `src/magic.c:1675` etc. INV-016 enforcement notes already document that heal sites intentionally skip `apply_position_change` because the broadcast lives in `damage()`, not on upward transitions. Contract currently enforced by construction; row pinned with regression test in the spirit of INV-017. Touched by: `mud/combat/engine.py:update_pos`, `mud/game_loop.py:char_update`, `mud/skills/handlers.py` heal handlers. | `tests/integration/test_inv019_position_promotion_on_heal.py` | ✅ ENFORCED |
| INV-017 | TICK-ITERATION-SAFETY | `src/update.c:char_update` (lines 661-872) iterates `char_list` with a pre-cached `ch_next = ch->next` (line 680) so the outer loop survives any lethal damage applied inside the per-char tick. The plague (line 846), poison (line 859), incap (line 866), and mortal (line 870) branches all call `damage(ch, ch, ...)` which routes to `raw_kill` and frees `ch`; the explicit comment at lines 788-792 ("MUST NOT refer to ch after damage taken, as it may be lethal damage (on NPC)") is the load-bearing contract — combined with the post-loop `IS_VALID(ch)` guard at line 884, ROM guarantees that subsequent characters in the tick still get processed even when an earlier one is extracted mid-iteration. | `mud/game_loop.py:char_update` iterates `for character in list(character_registry):` (line 690) — the `list(...)` snapshot is the Python equivalent of ROM's `ch_next` pre-cache, decoupling iteration from `character_registry.remove()` calls made by `mud/combat/death.py:raw_kill` (line 575) reachable through `_char_update_tick_effects` → `mud/combat/engine.py:apply_damage` → death branch. `_char_update_tick_effects` returns immediately after each `_damage()` call (no further `character` refs after the lethal hit, mirroring ROM's "MUST NOT refer to ch after damage taken" contract). The contract is currently enforced by construction; this row pins it down with a regression test so a future refactor that switches to live registry iteration (which would silently skip the post-mortem element under list-during-iteration mutation) fails loudly. Touched by: `mud/game_loop.py:char_update`, `mud/game_loop.py:_char_update_tick_effects`, `mud/combat/death.py:raw_kill`, `mud/combat/engine.py:apply_damage`. | `tests/integration/test_char_update_lethal_tick_iteration.py::test_lethal_poison_tick_does_not_skip_subsequent_npc` | ✅ ENFORCED |
| INV-016 | BCAST-ON-POSITION-TRANSITION | `src/fight.c:damage` is the canonical damage funnel. After it applies the hp delta and calls `update_pos` (handler.c:1380), it `act()`-broadcasts the position-change line per `src/fight.c:837-861` — "X is mortally wounded", "X is incapacitated", "X is stunned", "X is DEAD!!" Every ROM damage path (combat hits, spells, breath weapons, traps) routes through `damage()`, so the broadcast is the natural consequence of any hp drop that crosses a threshold. | (a) `mud/combat/engine.py:apply_damage` (the proper funnel, used by combat) calls `_position_change_message` → `_broadcast_pos_change` after `update_pos` — matches ROM exactly. (b) **Fixed (2.9.10)**: `mud/combat/engine.py:apply_position_change(victim, old_pos)` extracted as the shared enforcement point — broadcasts via `_position_change_message` (room) and `_push_message` (self) only when `victim.position != old_pos`. `_apply_damage` now delegates to it. Each `mud/skills/handlers.py` damage spell that bypasses `apply_damage` (16 sites: acid_blast, acid_breath, burning_hands, call_lightning, chill_touch, colour_spray, demonfire, dispel_evil, dispel_good, fire_breath, frost_breath, gas_breath, harm, heat_metal, lightning_breath, shocking_grasp) captures `old_pos = target.position` before the `hit -=` line and calls `apply_position_change(target, old_pos)` after `update_pos`. Heal sites (`cure_*`, `heal`) intentionally skip the helper — ROM's broadcast block lives in `damage()`, not on upward STUNNED → STANDING transitions. `cause_*` already routes through `apply_damage` and inherits the broadcast there. Touched by: `mud/combat/engine.py:apply_position_change`, `mud/combat/engine.py:_apply_damage`, every damage-spell handler in `mud/skills/handlers.py`. | `tests/integration/test_inv016_position_transition_broadcast.py::test_spell_damage_broadcasts_death_transition_to_room` | ✅ ENFORCED |
| INV-015 | AFFECT-EXPIRY-LIFECYCLE | **Consolidated 2.9.41** (was INV-015 AFFECT-TICK-LIFECYCLE + INV-018 WEAR-OFF-MESSAGE-FOR-RAW-AFFECT — two halves of the same per-affect expiry loop). **Stat-mod un-apply side**: `src/update.c:762-786 affect_update` decrements every `ch->affected` entry's duration. On expiry it calls `src/handler.c:1317 affect_remove`, which `affect_modify(ch, paf, FALSE)` (subtracts the stat modifier AND clears the bitvector in `affected_by`/`imm_flags`/`res_flags`/`vuln_flags`) → unlinks from `ch->affected` → `affect_check(ch, where, vector)` re-sets the bit only if another affect on `ch` or equipped objects still provides it. **Wear-off-message side**: `src/update.c:777-781` (same expiry loop) emits `skill_table[paf->type].msg_off` to the character whenever a positive-typed affect's duration reaches 0 — regardless of which apply path created the affect. ROM keys the message off the spell SN against the `skill_table`, not off the AFFECT_DATA struct, so every wear-off path lights the message: `apply_spell_effect`-equivalent landing (`spell_armor`, `spell_bless`, etc.) and bare `affect_to_char` landings (`src/update.c:828-840` plague-spread, food-borne poison transfers) alike. The two halves share one invariant: when a `ch->affected` entry's duration reaches 0, both the stat-mod must unwind AND the wear-off line must fire. | **Un-apply**: (a) `mud/handler.py:affect_remove(ch, paf)` mirrors `src/handler.c:1317` exactly — `affect_modify(False)` → `affected.remove(paf)` → `affect_check(where, vector)`. (b) `mud/affects/engine.py:tick_spell_effects` expiry branch routes ROM-canonical `AffectData` (integer `type`, no parallel `spell_effects` entry) through `affect_remove`. **Spell-effects-managed entries** (the `Character.apply_spell_effect` shadow-mirror path used by frenzy / bless / weaken / etc.) keep bare `affected.remove` — `remove_spell_effect` already runs `_apply_stat_modifier(-mod)` and `remove_affect(bitvector)`, so routing them through `affect_remove` would double-unwind (caught during 2.9.7 implementation by `tests/integration/test_spell_affects_persistence.py::TestSpellAffectPersistence::test_spell_affect_expires_after_duration` + `test_multi_entry_spell_wears_off_once_through_game_tick` + `tests/test_affects.py::test_affect_to_char_applies_stat_modifiers` regressions, hence the explicit split). **Wear-off message**: (c) `mud/affects/engine.py:tick_spell_effects` used to only emit a wear-off message when the expiring affect's name appeared in the `spell_effects` dict (the `apply_spell_effect` shadow-mirror path). Raw `AffectData` entries — written directly to `character.affected` without a parallel `apply_spell_effect` call — wore off silently, including the plague-spread case at `mud/game_loop.py:614-624`. **Fixed (2.9.14)**: new helper `mud/affects/engine.py:_lookup_raw_affect_wear_off(affect)` mirrors the precedent at `mud/game_loop.py:1121-1131 _broadcast_object_wear_off` — prefer an explicit `wear_off_message` attribute on the affect itself, then fall back to `skill_registry.get(affect.type).messages["wear_off"]`. The expiry branch of `tick_spell_effects` now calls it on raw AffectData paths; spell_effects-managed entries keep their existing `effects[spell_name].wear_off_message` lookup. Touched by: `mud/affects/engine.py:tick_spell_effects`, `mud/affects/engine.py:_lookup_raw_affect_wear_off`, `mud/handler.py:affect_remove`. | `tests/integration/test_inv015_affect_tick_lifecycle.py` + `tests/integration/test_inv018_wear_off_message_for_raw_affect.py` | ✅ ENFORCED |
| INV-014 | OBJECT-REGISTRY-LIFECYCLE | **Consolidated 2.9.41** (was INV-014 OBJECT-REGISTRY-MEMBERSHIP + INV-021 OBJECT-EXTRACT-RECURSIVE — two halves of the same `object_list` contract). **Creation side**: `src/db.c:create_object` appends every freshly built `OBJ_DATA` to the global `object_list` unconditionally — every world-scan consumer (`src/magic.c:3737 spell_locate_object`, decay sweep, save) iterates that list, so any obj built without registration is invisible to the world. **Extract side**: `src/handler.c:2052-2086 extract_obj` detaches the object from its current container (room/char/obj), then iterates `obj->contains` and **recursively calls itself** on every child BEFORE removing the outer object from `object_list` — otherwise contained items survive in the world-scan registry while their carrier is freed. The two halves share one invariant: every Object lives in `object_registry` exactly while it's part of the world. | **Creation**: (a) `mud/models/object.py:create_object(prototype, *, instance_id=None) -> Object` is the canonical Python factory: it constructs the `Object` and appends to `mud.models.obj.object_registry`. (b) Every direct `Object(...)` construction site in production routes through it — `mud/spawning/obj_spawner.py:spawn_object` (inline append, pre-existing), `mud/handler.py:create_money`, `mud/combat/death.py:_fallback_gore`, `mud/combat/death.py:_fallback_corpse`, `mud/rom_api.py:recursive_clone`, `mud/commands/shop.py:_clone_inventory_object` (fallback path when `spawn_object` returns `None`), `mud/models/conversion.py:load_objects_for_character` (DB-restored inventory). (c) `mud/skills/handlers.py:_iterate_world_objects` walks `object_registry` first (computing the holder per ROM `src/magic.c:3747` — outermost `in_obj` chain, then prefer `carried_by` over `in_room`); a legacy room/character secondary walk remains as a compat backstop for unit tests that build `Object` directly without registering. The symptom that surfaced this: `locate object` could not find a freshly-created corpse, money pile, or shop-clone item because those bypassed the registry. **Extract**: (d) `mud/game_loop.py:_extract_obj` (lines 982-1005) recurses into `getattr(obj, "contains", [])` first (line 983-984), then detaches from carrier/room/parent-container, then removes from `mud.models.obj.object_registry` (line 1004-1005). Recursion depth is unbounded by design — matches ROM. (e) Caller surface: 6 import sites all route through this canonical (`mud/mob_cmds.py:238`, `mud/combat/engine.py:976`, `mud/magic/effects.py:56`, `mud/world/movement.py:620`, `mud/commands/obj_manipulation.py:669`, `mud/game_loop.py` internal). No caller open-codes its own extract loop. Touched by: `mud/models/object.py:create_object`, `mud/game_loop.py:_extract_obj`, `mud/models/obj.py:object_registry`, every creation + extract import site. | `tests/integration/test_inv014_object_registry_membership.py` + `tests/integration/test_inv021_object_extract_recursive.py` | ✅ ENFORCED |

## Action items

1. ~~**Write enforcement tests** for INV-005 (same-room combat) and
   INV-006 (fighting-pointer coherence after death).~~ **Done in 2.7.4**
   — see `tests/integration/test_inv005_same_room_combat.py` and
   `tests/integration/test_inv006_fighting_pointer_coherence.py`.
2. ~~**Decide on INV-007**: either codify as a `pytest -k` check (e.g.
   `tests/test_rng_determinism.py` greps for `random.` in `mud/combat/`)
   or accept it as convention and note in CONTRIBUTING.~~ **Done in 2.7.5**
   — `tests/test_rng_determinism.py` scans `mud/combat/`, `mud/skills/`,
   `mud/spells/`; vestigial `Random` removed from `SkillRegistry` as prerequisite.
3. ~~**Resolve INV-008** by consolidating the two `load_character`
   paths.~~ **Fully resolved in 2.8.3.** First closed in 2.7.6 with
   the JSON pfile as canonical and the DB demoted to auth-only; that
   hybrid had a hidden seam at `create_character` / `Character.from_orm`,
   which still wrote/read the DB row at first-login. Reversed in three
   phases: 2.8.0 extended the `Character` SQLAlchemy model with 39
   columns covering every `PlayerSave` field (incl. JSON columns for
   skills/affects/aliases/inventory/equipment); 2.8.1 swapped
   `account_manager.save_character` / `load_character` to the DB path
   and removed the JSON pfile delegation; 2.8.3 extracted the remaining
   helpers from the stub (`time_info` → `mud/world/time_persistence.py`,
   serializers → `mud/db/serializers.py`) and deleted `mud/persistence.py`
   entirely. See `docs/parity/INV008_REVERSAL_AUDIT.md` for the
   71-field map that drove the reversal.

## Retired IDs (consolidated)

These IDs are still referenced by CHANGELOG entries and commit
messages — kept as forward pointers so historical references resolve.
The underlying enforcement tests are unchanged (the merged row in the
active table lists them).

- **INV-018** WEAR-OFF-MESSAGE-FOR-RAW-AFFECT → merged into **INV-015**
  AFFECT-EXPIRY-LIFECYCLE on 2.9.41. Both halves were enforced on the
  same `tick_spell_effects` expiry loop. Test
  `tests/integration/test_inv018_wear_off_message_for_raw_affect.py`
  still runs.
- **INV-021** OBJECT-EXTRACT-RECURSIVE → merged into **INV-014**
  OBJECT-REGISTRY-LIFECYCLE on 2.9.41. Both halves were enforced on
  the same `object_registry` lifecycle. Test
  `tests/integration/test_inv021_object_extract_recursive.py` still
  runs.
- **INV-023** AREA-NPLAYER-COHERENCE → merged into **INV-010**
  ROOM-PEOPLE-COHERENCE on 2.9.41. Both halves were enforced on the
  same `char_from_room` / `char_to_room` mutation pair. Test
  `tests/integration/test_inv023_area_nplayer_coherence.py` still
  runs.

## Stale-row footnotes (linked from `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`)

These rows in the per-file tracker were correct *for the per-file
audit* but missed cross-file invariants. The per-file rating stays;
the cross-file work is tracked here.

- **`comm.c` (95% per-file)**: INV-001 (now ✅), INV-002 (now ✅).
  Pre-fix the row was misleading because both invariants were broken
  in code outside `comm.c` itself.
- **`fight.c` (95% per-file)**: INV-001 root cause lived in
  `mud/combat/engine.py` (the audit row's primary Python file) but
  surfaced as a `comm.c` symptom. INV-005 and INV-006 are now both
  enforced by dedicated integration tests. Open FIGHT-XXX gaps
  (`do_kill → multi_hit`, `is_safe()` inside `damage()`) have also
  been closed in the file audit.
- **`save.c` (100% per-file)**: row points only at
  `mud/persistence.py`. INV-003 was broken in
  `mud/account/account_manager.py` (the production path), not the
  audited file. INV-008 tracks the broader divergence between the
  two implementations.

## Watch list

**✅ ENFORCED: INV-027 — ACT-PERS-NAME-MASKING (per-recipient subset)** (surfaced 2026-05-27 during the BCAST wiz/imm probe as "ACT-INVIS-TRUST-GATE"; ROM mechanism CORRECTED + re-scoped 2026-05-29; PROBED 2026-05-29 — violation confirmed, enforcement attempted + reverted, blocker pinned on a `can_see_character` room-None reconciliation; **prerequisite VISION-001 landed 2.11.33 and enforcement landed 2.11.34**). Per-recipient `$n`/`$N` masking now routes through `can_see_character`; the broadcast-once `recipient=None` path stays the documented MESSAGE_DELIVERY.md divergence. See the "Enforcement outcome (2026-05-29)" bullet below.

**Enforcement point**: `mud/utils/act.py:_pers` (gated on `viewer is not None`). **Test**: `tests/integration/test_inv027_act_pers_name_masking.py` (masking + `recipient=None` boundary). **Prerequisite**: VISION-001 (`docs/parity/HANDLER_C_AUDIT.md`).

> **⚠️ CORRECTION (2026-05-29).** The original framing of this candidate
> (below, struck) claimed `act()` *suppresses the whole line* for sub-trust
> witnesses via a per-recipient `get_trust(rch) >= ch->invis_level` filter
> inside `act()`. **That ROM mechanism is wrong** — verified against primary
> source. ROM `act_new` (`src/comm.c:2230-2244`) delivers the line to **every**
> eligible recipient in the room; there is no `invis_level` filter in the
> recipient loop. Visibility is handled by the **`$n`/`$N` name substitution**:
> `PERS(ch, to)` (`src/merc.h:2145`) → `can_see(to, ch)` (`src/handler.c:2618-2625`,
> which returns FALSE when `get_trust(to) < ch->invis_level`), so a sub-trust
> witness receives the line with the actor's name rendered as **"someone"**, NOT
> nothing. Implementing the original "suppress for sub-trust" proposal would have
> made the port *diverge* from ROM for generic `act(TO_ROOM)` broadcasts. The
> *line-suppression* behavior is real but lives **per-command** in
> `do_goto`/`do_violate` (`src/act_wiz.c:969-994,1026-1057`), which loop room
> occupants and call `act(..., rch, TO_VICT)` only where
> `get_trust(rch) >= ch->invis_level` — that contract is now tracked as
> **WIZ-045** (`do_goto`, ✅ FIXED 2.11.30) and **WIZ-046** (`do_violate`, ⚠️ open)
> in `docs/parity/ACT_WIZ_C_AUDIT.md`, not here. Two commands share that gate, so
> it could itself firm into an invariant if more `act_wiz` surface uses it.

- **Corrected ROM mechanism (the actual cross-file contract)**: every `act()`
  `$n`/`$N` name substitution must route through `PERS`→`can_see`, so an actor
  the recipient cannot see (wiz-invis `invis_level`, `AFF_INVISIBLE`, dark room,
  blind/sneak/hide) renders as **"someone"** — while the line itself is still
  delivered. This is name-masking, not line-suppression.
- **Python state (2.11.30)**: only the combat path is faithful —
  `mud/combat/messages.py` and `mud/combat/engine.py:856` use
  `mud/world/vision.py:pers()` (full `can_see`). The other `act()`-style paths
  do **not** mask:
  - `mud/utils/act.py:act_format` (used by `mud/spec_funs.py`, `mud/wiznet.py`,
    `mud/net/connection.py`, `mud/world/movement.py`, `mud/music/__init__.py`)
    has a **local `_pers` (lines 56-73) that returns the name unconditionally** —
    no `can_see`. Note `mud/world/movement.py:107` even *documents* the intent
    ("use act_format so invisible …") that the helper does not deliver — a latent
    bug. The fix is to route `act_format`'s `$n`/`$N` through `vision.pers()`
    (and `$p`/`$P` through `can_see_object`, already partly done via `_object_name`).
  - `mud/commands/imm_commands.py:_act_room` does `message.replace("$n", char.name)`
    unconditionally (leaks the name); `mud/commands/imm_display.py:_act_room`
    instead *gates* delivery on `can_see_character` (wrongly **suppresses** the
    whole line — the original mis-framing's behavior).
- **Corrected proposed enforcement (when promoted)**: do **not** route
  `broadcast_room` through a suppress filter — `broadcast_room`
  (`mud/net/protocol.py:58`) receives a **pre-formatted string** and has no
  per-recipient `$n` rendering, so masking is impossible there; it must happen at
  the per-recipient formatter (`act_format` / `_act_room`). Make `act_format`'s
  `_pers` delegate to `vision.pers()`; reconcile the two `_act_room` helpers onto
  the same PERS semantics. Regression: an actor with `invis_level=60` (or
  `AFF_INVISIBLE`) emits a TO_ROOM `$n` line; a non-seeing witness receives the
  line **with "someone"** (not nothing), a seeing witness receives the name.
  Filename slot: `tests/integration/test_inv027_act_pers_name_masking.py`.
- **Why still deferred**: wide blast radius (`spec_funs`, `wiznet`, `connection`,
  `movement`, `music` all call `act_format`), and it needs its own probe to
  separate per-recipient callers (where masking applies) from broadcast-once
  callers (`recipient=None` → fed to `broadcast_room`, where ROM's per-recipient
  PERS cannot be reproduced without restructuring — the MESSAGE_DELIVERY.md
  architectural divergence). Out of scope for the WIZ-045 close that corrected it.
- **Risk if left unenforced**: an invisible/wiz-invis actor's **name** leaks to
  witnesses who shouldn't see it across `act_format`/`_act_room` broadcasts
  (movement, give, spec_fun narration, etc.) — they should read "someone".
- **Probe outcome (2026-05-29) — violation CONFIRMED; enforcement ATTEMPTED +
  REVERTED; blocker PINNED.** The probe separated the caller classes (per-recipient
  vs `recipient=None` broadcast-once, as the deferral note asked) and verified the
  ROM contract against primary source: `act_new` `$n`/`$N` → `PERS(ch, looker)`
  (`src/merc.h:2145`) → `can_see(looker, ch)` (`src/handler.c:2618-2664`), for both
  generic `act(TO_ROOM)` **and** wiznet (`src/act_wiz.c:188` passes the actor as
  `vch`, so `$N` is PERS-masked per listener). So masking is the correct ROM
  mechanism. The obvious fix — route `act_format._pers` through
  `mud/world/vision.py:can_see_character`, gated on `viewer is not None` — was
  implemented and **fails the full suite with 15 regressions** (`test_wiznet` ×7,
  `test_account_auth` ×4, `test_spec_funs` ×4):
  - **Pinned blocker — roomless synthetic actors trip `can_see_character`'s
    room-None bail.** `mud/world/vision.py:can_see_character:161-164` returns
    `False` when `observer.room is None or target.room is None`. ROM `can_see`
    (`src/handler.c:2618-2664`) has **no `victim->in_room` check at all** and only
    dereferences `ch->in_room` for the dark check (`:2638`), after the
    trust/incog/holylight/blind gates — ROM playing chars always have rooms, so the
    branch handles a state ROM never reaches. Python's wiznet path **deliberately
    passes roomless actors**: `announce_wiznet_new_player`
    (`mud/net/connection.py:207`) builds a `SimpleNamespace(name=…, sex=…)`
    placeholder with no room. Routing `_pers` through `can_see_character` therefore
    renders **"Newbie alert! someone sighted."** / **"someone groks the fullness of
    his link."** in production — a real user-facing regression, not a test artifact.
  - **Secondary**: `test_wiznet`/`test_spec_funs` construct actors as
    `SimpleNamespace` without `room`/`has_affect`, so `can_see_character` either
    over-masks (room-None) or raises `AttributeError` even where masking would be
    ROM-correct (same-room invisible bite). Any future enforcement needs those mocks
    upgraded to real `Character`s (or `has_affect`-bearing).
  - **Prerequisite for enforcement (own gap, own test, own impact pass — do NOT
    bundle into the `_pers` change):** reconcile `can_see_character`'s room-None
    handling with ROM `can_see` ordering (trust/incog/holylight before any
    room/dark logic; no `victim->in_room` bail), **and/or** have wiznet pass real
    in-room actors (or bake names for synthetic placeholders). `can_see_character`
    is the core visibility helper (43 direct `act_format` callers; combat also uses
    `vision.pers`), so its room-None semantics have no ROM ground truth and changing
    them is a design decision requiring its own failing test + `gitnexus_impact`.
  - **Contract locked**: `tests/integration/test_inv027_act_pers_name_masking.py`
    holds the same-room masking assertion as a **strict `xfail`** (reason names this
    blocker) plus a passing `recipient=None` boundary guard. Remove the `xfail`
    marker when the prerequisite lands. `act_format._pers` carries an INV-027 NOTE
    pointing here. **Status stays OPEN** — the per-recipient subset is the only part
    that could be enforced, and even it is blocked; broadcast-once stays divergent by
    MESSAGE_DELIVERY architecture.
- **Enforcement outcome (2026-05-29) — ✅ ENFORCED (per-recipient subset).** The
  pinned blocker was cleared by **VISION-001** (2.11.33,
  `docs/parity/HANDLER_C_AUDIT.md` "Stable-ID Divergences — `can_see()`"):
  `can_see_character` no longer bails when the **target** is roomless, matching ROM
  `can_see` (`src/handler.c:2618-2664`, which never checks `victim->in_room`). A
  28-direct-caller census confirmed no descriptor/registry/`room.people` iterator can
  observe a roomless target except the intentional synthetic wiznet subjects, so the
  loosen is safe (full suite green). With that prerequisite in place (2.11.34):
  - `mud/utils/act.py:_pers` now routes `$n`/`$N` through `can_see_character` when
    `viewer is not None and target is not viewer` (returns `"someone"` on failure).
    The `recipient=None` broadcast-once path keeps the name (no viewer to gate
    against — the MESSAGE_DELIVERY.md divergence; the boundary test pins it).
  - `announce_wiznet_new_player` (`mud/net/connection.py`) now builds a **real
    roomless `Character`** as the newbie-alert subject instead of a `SimpleNamespace`,
    so `$N` renders the real name via VISION-001 (ROM `nanny.c:547` passes the real
    roomless `ch`) and `can_see_character`'s `has_affect`/`invis_level` reads don't
    raise.
  - The 15 previously-regressing tests were the predicted set (`test_wiznet` ×7,
    `test_account_auth` ×4, `test_spec_funs` ×4). Root cause: their mock recipients
    were roomless real `Character`s (→ masked) or bare `SimpleNamespace` without
    `has_affect` (→ AttributeError once VISION-001 removed the early bail). Fixed by
    rooming the mock listeners in lit rooms / adding a no-affect `has_affect` stub —
    matching production (real roomed immortals). Expected strings unchanged (real
    names), so the tests still assert the production scenario; the dedicated INV-027
    test (real `Character`s) locks the masking contract.
  - The `xfail` marker on `test_act_pers_masks_invisible_actor_name_for_nonseeing_recipient`
    is removed; it is now a passing test. Full suite: 4989 passed, 4 skipped, 0 xfailed.
  - **Scope**: the per-recipient subset is ENFORCED. The broadcast-once
    (`recipient=None`) path remains the documented MESSAGE_DELIVERY.md architectural
    divergence (pinned by the boundary test). The two `_act_room` helpers
    (`imm_commands.py` vs `imm_display.py`) are not part of this enforcement — their
    PERS reconciliation, if pursued, is separate.

<details><summary>Original (incorrect) framing — retained for the audit trail</summary>

~~**ACT-INVIS-TRUST-GATE** — ROM mechanism: `src/comm.c:act()` filters every
recipient by `get_trust(rch) >= ch->invis_level` inside `act()`, so sub-trust
witnesses receive nothing. Proposed: a `_can_witness(actor, witness)` helper
routing `_act_room` and `broadcast_room` through `get_trust(witness) >=
invis_level`; test asserts a trust=10 witness sees nothing.~~ Wrong — see the
correction above: `act()` does not filter recipients; it masks the `$n` name via
PERS/can_see. Line-suppression is per-command (`do_goto`/`do_violate` → WIZ-045/046).
</details>

**~~Open: INV-028 candidate — LIGHT-SLOT-KEY-COHERENCE~~ ENFORCED 2.9.85** (test `tests/integration/test_inv028_light_slot_key_coherence.py`; see the active table row above). `do_wear` now routes `ITEM_LIGHT` into `WearLocation.LIGHT` (ROM `act_obj.c:1415-1422`), and both readers tolerate the int/str key forms. Candidate analysis retained below for the audit trail.**

- **ROM mechanism**: ROM equips a worn light into the single `WEAR_LIGHT`
  slot (`src/act_obj.c:wear_obj` → `equip_char(ch, obj, WEAR_LIGHT)`), and
  every consumer reads that same slot via `get_eq_char(ch, WEAR_LIGHT)`:
  room-light accounting (`src/handler.c:1504-1507` char_from_room /
  `1571-1573` char_to_room) and the per-tick burnout decay
  (`src/update.c:721-730`). One slot constant, used consistently across
  equip, room-light tracking, and decay.
- **Python pre-state (2.9.81)**: the LIGHT equipment slot is keyed **three
  inconsistent ways**, so no single production path satisfies all consumers:
  - `do_wear` (`mud/commands/equipment.py:173-219`) routes any HOLD-flagged
    item — **including lights** — into `int(WearLocation.HOLD)` and emits
    "You light $p and hold it"; it never writes `WearLocation.LIGHT`.
    `_get_wear_location` (`equipment.py:534-591`) has **no LIGHT branch** at
    all, so a light lacking the HOLD flag is simply "You can't wear that."
  - `Room._has_lit_light_source` (`mud/models/room.py:29`) looks up the
    light under the **string** key `str(int(WearLocation.LIGHT))` == `"0"`.
  - `_find_equipped_light` (`mud/game_loop.py:348-365`) matches only the
    literal str `"light"` or a **non-str** slot whose `int(slot) ==
    int(WearLocation.LIGHT)` — it matches neither `"0"` nor the HOLD key.
- **Consequence**: a PC who `wear`/`hold`s a light gets it in the HOLD slot,
  where neither room-light tracking nor burnout decay sees it. The decay
  loop is additionally PC-only (`mud/game_loop.py` skips `is_npc`), and PCs
  only acquire equipment via `do_wear`, so `_decay_worn_light`'s burnout
  branch (the ARITH-202 site) is effectively **unreachable in production**.
  The existing `tests/integration/test_room_light_tracking.py` cases pass
  only because they hand-key equipment under `"0"` (str) and exercise
  `Room.add_character` directly — they never drive `_decay_worn_light`.
- **Touched by (probe evidence)**: surfaced while closing **ARITH-202**
  (worn-light burnout `--room->light` floor removal, `game_loop.py:454`).
  The ARITH-202 fix is ROM-faithful arithmetic but reaches the live game
  only once equipment is keyed under `WearLocation.LIGHT`; its regression
  test had to equip under the IntEnum key to make `_find_equipped_light`
  match. `mud/world/look.py:224`, `mud/commands/inventory.py:844`,
  `mud/utils/olc_tables.py:19/47`, `mud/commands/build.py:636/663` all
  reference the LIGHT slot/flag and would need to agree on the canonical key.
- **Proposed enforcement (when promoted)**: adopt `int(WearLocation.LIGHT)`
  as the one canonical key (matching the rest of `do_wear`, which stores
  `int(wear_loc)` keys); add a `do_wear` LIGHT branch that equips
  `ITEM_LIGHT` into `WearLocation.LIGHT` mirroring ROM `wear_obj`; make
  `Room._has_lit_light_source` and `_find_equipped_light` read that same
  int key. Regression: `tests/integration/test_inv028_light_slot_key_coherence.py`
  — `do_wear` a lit torch → lands in `WearLocation.LIGHT`; `room.light`
  increments on enter; a burnout tick decrements `room.light` and destroys
  the torch.
- **Why deferred**: closing it means reconciling `do_wear`'s HOLD-vs-LIGHT
  routing against ROM `wear_obj` and unifying the slot key across three
  modules — a focused cross-module change, out of scope for the ARITH
  arithmetic-floor close-out that surfaced it.
- **Risk if left unenforced**: PC light sources never burn out and PC-held
  lights are mis-counted (or uncounted) in room lighting vs ROM — a
  player-visible parity gap.

**Open: INV-025 follow-up — broaden mp_act_trigger_room dispatch beyond do_emote.**

- ~~INV-025 candidate (MOBPROG-ACT-TRIGGER-DISPATCH)~~ **enforced 2.9.40**.
  MOBtrigger global + `disable_mobtrigger()` context manager + `mp_act_trigger_room`
  per-room dispatcher landed in `mud/mobprog.py`; `do_emote` is the first
  callsite wired. Three regression tests pin the contract:
  (1) PC emote fires TRIG_ACT on listening NPC,
  (2) `disable_mobtrigger()` context suppresses dispatch,
  (3) NPC emoter does not self-fire its own TRIG_ACT.
  **Follow-up sweep** (not yet scoped as an INV row — the contract is
  locked): remaining ROM act() callsites in Python that should also feed
  `mp_act_trigger_room`. Closed so far (one-callsite-per-commit): `do_give`,
  `do_drop`, `do_get`, `do_put`, `do_sacrifice`,
  `do_wear`/`do_remove`/`do_wield`/`do_hold`, position-transition
  broadcasts (`mud/combat/engine.py:apply_position_change` →
  `_broadcast_pos_change`), and **combat `dam_message`**
  (`mud/combat/engine.py:_broadcast_damage_messages`, closed as `FIGHT-018`
  in 2.9.90 — every combat hit fires TRIG_ACT on room NPCs, ROM
  `src/fight.c:2215-2226`, no `MOBtrigger` wrap). Still open: the broader
  `_push_message`/`broadcast_room` narration surface (non-combat act()
  lines). Each is gated by whether the matching ROM site uses
  `MOBtrigger = FALSE` around its act() emission (do_give does;
  drop/get/put/dam_message do not). Track as ad-hoc follow-up commits
  rather than a new INV row.
- ~~PORTAL-TRAVEL-OBJ-DECAY (probed 2.9.39)~~: charge depletion in
  `mud/world/movement.py:580-584` reads/writes `portal.value[0]` on the
  instance (not the prototype); timer-decay in `mud/game_loop.py:1157-1188`
  honours `timer <= 0` as "no decay armed" and routes through `_extract_obj`
  (covered by INV-013/INV-021). No gap surfaced. Not filed.

- ~~**Dual `Object` / `ObjectData` classes**~~ **Closed as INV-012 in
  2.9.0.** Spec at `docs/superpowers/specs/2026-05-24-object-objectdata-consolidation-design.md`;
  plan at `docs/superpowers/plans/2026-05-24-object-objectdata-consolidation.md`.
  17 commits across 5 phases: extend Object with ROM-named fields,
  populate object_registry at spawn (this is where the production
  no-op bugs flipped to working code — locate-object, mobprog oload,
  decay tick), retype game_loop/handler/skills/music/ai helpers,
  collapse 12 isinstance(ObjectData) branches, migrate 35 test
  fixtures across 9 files, then delete ObjectData entirely.

**Surfaced 2026-05-24 while closing INV-010; CARRY-WEIGHT entry now
closed as INV-011 below — kept here for the audit trail.**

- ~~An object-side analogue of INV-003: every `Object` creation path
  should append to a canonical `object_list` and `extract_obj` should
  remove it from every container.~~ Subsumed by the **Dual `Object` /
  `ObjectData`** entry above — the deeper root cause is the dual-class
  divergence, not the registry hygiene.
- ~~`carry_weight` / `carry_number` coherence with `char.inventory`
  across every get/drop/give/equip/unequip path.~~ **Closed as INV-011
  in 2.8.79.**

## Maintenance

**22 of ~20 budget — over by two after the 2.9.41 consolidation.** Three dual pairs merged (each freed one slot, no contract lost): INV-014 + INV-021 → INV-014 OBJECT-REGISTRY-LIFECYCLE (creation + extract on `object_registry`); INV-015 + INV-018 → INV-015 AFFECT-EXPIRY-LIFECYCLE (stat-mod un-apply + wear-off message on the same expiry loop); INV-010 + INV-023 → INV-010 ROOM-PEOPLE-COHERENCE (bidirectional coherence + area.nplayer accounting on `char_from_room`/`char_to_room`). The retired IDs (INV-021, INV-018, INV-023) are left as forward-pointer stubs below the active table so historical CHANGELOG references and commit messages still resolve. Both regression tests survive the merge — the merged row lists both. INV-001 + INV-002 were *not* merged: the 2.9.39 footer mis-described them as "message-delivery duals" but INV-001 is SINGLE-DELIVERY (broadcast routing) while INV-002 is PROMPT-CLAMP (display formatting after raw_kill clamps `hit >= 1`). They share no enforcement point. Going forward: probe-then-scope continues. If/when count crosses ~25 again, the next consolidation candidates would be (a) INV-016 / INV-019 (position-transition broadcast / silent promotion-on-heal duals) and (b) INV-006 / INV-009 (fighting-pointer coherence after death / registry-disconnect cleanup — both on `character_registry` membership transitions). Neither is being merged now — both still pin distinct enforcement points.

This tracker is small on purpose. If it grows past ~20 invariants,
something has gone wrong with the per-file audit methodology and the
two trackers should be merged or restructured. Discuss before adding
INV-021.
