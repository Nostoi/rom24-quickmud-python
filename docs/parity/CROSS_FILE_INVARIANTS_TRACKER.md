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
| INV-001 | SINGLE-DELIVERY | `src/comm.c:write_to_buffer` writes once per message | `mud/combat/engine.py:_push_message` returns after async send when `connection` exists | `tests/integration/test_message_delivery_no_duplicate.py` | ✅ ENFORCED |
| INV-002 | PROMPT-CLAMP | `src/comm.c:1420ff bust_a_prompt` runs after `src/fight.c:1718 raw_kill` clamps `hit >= 1` (single-threaded) | `mud/utils/prompt.py` clamps display to `max(0, hit)` at both render sites | `tests/test_prompt_clamps_hp.py` | ✅ ENFORCED |
| INV-003 | REGISTRY-MEMBERSHIP | `src/save.c:fread_char` appends to `char_list`; pulse handlers iterate it | Every `load_character` path appends to `mud.models.character.character_registry` | `tests/integration/test_character_creation_runtime.py::TestCharacterRegistryRegistration` | ✅ ENFORCED |
| INV-004 | PC-CONNECTION-SURVIVES-DEATH | `src/handler.c:2103-2187 extract_char(ch, FALSE)` keeps PC descriptor open | `mud/combat/death.py:raw_kill` does not touch `char.connection`; PC stays in registry | `tests/integration/test_pc_death_keeps_connection.py` | ✅ ENFORCED |
| INV-005 | SAME-ROOM-COMBAT-ONLY | `src/fight.c:violence_update` skips if `ch->in_room != victim->in_room` | `mud/game_loop.py:violence_tick` checks `attacker.room == victim.room` before `multi_hit` | `tests/integration/test_inv005_same_room_combat.py` | ✅ ENFORCED |
| INV-006 | FIGHTING-POINTER-COHERENCE | `src/fight.c:stop_fighting(victim, TRUE)` sweeps `char_list`, clears every `fch->fighting == victim` | `mud/combat/engine.py:stop_fighting(ch, both=True)` iterates `character_registry` | `tests/integration/test_inv006_fighting_pointer_coherence.py` | ✅ ENFORCED |
| INV-007 | RNG-DETERMINISM | `src/db.c init_mm` Mitchell-Moore RNG is the only source of combat/affect rolls | All `mud/combat/`, `mud/skills/`, `mud/spells/` use `mud.math.rng_mm.number_*`; never `random.*` | `tests/test_rng_determinism.py` | ✅ ENFORCED |
| INV-008 | DUAL-LOAD-CHARACTER-COHERENCE | (Python-only) Single canonical store for player state; no dual JSON-pfile / DB-row split | `mud/db/models.py:Character` is canonical (39 + base columns); `mud/account/account_manager.py:save_character` calls `save_character_to_db` (UPDATE), `load_character` queries the DB and runs `Character.from_orm`; serialization helpers live in `mud/db/serializers.py`; time-info persistence in `mud/world/time_persistence.py`; `mud/persistence.py` deleted (2.8.3) | `tests/integration/test_inv008_persistence_coherence.py` + `tests/integration/test_db_canonical_round_trip.py` | ✅ ENFORCED |
| INV-009 | REGISTRY-DISCONNECT-CLEANUP | `src/comm.c:close_socket` + `src/nanny.c:do_quit` ensure char_list has at most one entry per player name at any time; reconnects rebind via `check_reconnect` rather than appending duplicates | (a) `mud/account/account_manager.py:load_character` dedupes by `name` before appending — drops any prior `character_registry` entry with the same name (e.g. the level=0 bare-row Character loaded during the nanny name/password phase) before adding the freshly-loaded one. (b) `mud/net/connection.py` disconnect cleanup (websocket + telnet `finally` blocks) removes the Character from `character_registry` on non-forced disconnect, matching the `save + char_from_room + release_account` quit semantics already in place. Forced disconnects (descriptor takeover via `_disconnect_session`) skip removal — the Character transfers to the new descriptor. | `tests/integration/test_inv009_registry_disconnect_cleanup.py` | ✅ ENFORCED |
| INV-010 | ROOM-PEOPLE-COHERENCE | `src/handler.c:1497-1573 char_from_room / char_to_room` are the only mutation paths; bidirectional contract — every `ch->in_room == R` lives in `R->people`, every entry in `R->people` has `ch->in_room == R`. ROM also relies on a single canonical `room_index_hash` lookup table (`src/db.c:get_room_index`). | (a) `mud/models/room.py:Room.add_character` / `Room.remove_character` keep the bidirectional state synchronized and own area.nplayer + light-source accounting. (b) `mud/models/room.py:char_to_room` wraps `add_character` with a NULL → temple fallback. (c) `mud/models/room.py` no longer declares a second `room_registry` dict; it re-imports the canonical `mud.registry.room_registry`, so the temple fallback and `mud/game_loop.py:525` limbo lookup read from the world-loaded registry rather than a perpetually empty one (fixed in 2.8.78). Touched by: `mud/spec_funs.py` (mayor patrol), `mud/spawning/templates.py:MobInstance.move_to_room`, `mud/commands/session.py:do_recall`, `mud/commands/imm_load.py`, `mud/commands/imm_search.py`, `mud/commands/imm_commands.py:_char_from_room/_char_to_room`. | `tests/integration/test_inv010_room_people_coherence.py` | ✅ ENFORCED |
| INV-011 | CARRY-WEIGHT-COHERENCE | `src/handler.c:1626 obj_to_char` / `1642 obj_from_char` keep `ch->carry_weight` and `ch->carry_number` in lockstep with `ch->carrying`. `extract_obj` (`src/handler.c:2051,2058-2059`) routes through `obj_from_char` so the counters never drift. | (a) `Character.add_object` / `Character.equip_object` / `Character.remove_object` (mud/models/character.py:542-566) call `_recalculate_carry_weight` and adjust `carry_number`. (b) `mud/game_loop.py:_remove_from_character` (used by `_extract_obj` → carrier branch and by corpse decay) also re-derives `carry_weight` via `_recalculate_carry_weight` and decrements `carry_number` by the obj's slot cost (fixed in 2.8.79 — previously dropped the obj from inventory/equipment without touching the cached counters, so every extract on a carried object skewed encumbrance upward). Touched by: `mud/game_loop.py:_extract_obj` and `_decay_carried_light`, `mud/mob_cmds.py:1095-1110` (mpoload-style cleanup), `mud/combat/engine.py:991` (corpse extract), `mud/mob_cmds.py:do_mpoload` inventory branch (fixed in 2.9.4 — previously appended directly to `ch.inventory` without going through `add_object`, drifting `carry_weight` / `carry_number` on every MOBprog `mob oload <vnum>`). | `tests/integration/test_inv011_carry_weight_coherence.py` | ✅ ENFORCED |
| INV-013 | OBJECT-LOCATION-COHERENCE | `src/handler.c:1626 obj_to_char`, `1953 obj_to_room`, `1968 obj_to_obj` keep `in_room`, `carried_by`, `in_obj` mutually exclusive — every set on one clears the other two. `obj_from_room` / `obj_from_char` / `obj_from_obj` each clear exactly one field. ROM has no "location" concept distinct from these three. | (a) `Object.location` (mud/models/object.py) is no longer a stored field; it is a property dispatching to `in_room` / `carried_by` / `in_obj` based on the target type (Room → in_room, Character → carried_by, Object → in_obj, None → clear all three). Reads return whichever ROM field is non-None. (b) Bug surfaced during conversion: `MobInstance.add_to_inventory` (mud/spawning/templates.py:442) set `obj.carried_by = mob` then `obj.location = None`, which under the new dispatch cleared carried_by — the `obj.location = None` line was deleted. (c) Bug surfaced during conversion: `make_corpse` (mud/combat/death.py:441) set `money_obj.location = None` while appending to `corpse.contained_items`; per ROM's obj_to_obj, money inside a corpse must have `in_obj = corpse` — fixed to `money_obj.location = corpse`. (d) `mud/handler.py:638` defensive bridge `getattr(obj, "in_room", None) or getattr(obj, "location", None)` becomes redundant — left in place for resilience, harmless. (e) `mud/models/character.py:Character.add_object` now sets `obj.location = self` after the inventory append (fixed in 2.9.4 — previously updated carry counters but left the canonical `carried_by` field unset, so every direct `add_object` caller silently produced an inventory item with no carrier back-pointer). (f) `Character.equip_object` sets `obj.carried_by = self`, and `Character.remove_object` clears it (fixed in 2.9.5 — previously equip left it at whatever the inventory path had set, and remove left a stale back-pointer to the former carrier; ROM `equip_char` keeps the carrier set, `obj_from_char` clears it atomically). Touched by: every Object.location read/write across mud/ — semantically converged through the property, no caller sweep required. | `tests/integration/test_inv013_object_location_coherence.py` | ✅ ENFORCED |
| INV-012 | OBJECT-LIST-CANONICAL | `src/db.c:create_object` appends every new `OBJ_DATA` to the global `object_list`; `src/handler.c:2051 extract_obj` removes (recursively for contents via lines 2063-2067). ROM has ONE struct, ONE list, four exclusive containers (`in_room`, `carried_by`, `in_obj`, equipped via `wear_loc`). | (a) `mud/models/object.py:Object` is the only runtime class. `mud/models/obj.py:ObjectData` deleted in 2.9.0; the dual-class divergence (parallel to INV-008) is closed. (b) ROM-named container fields `in_room`, `in_obj`, `carried_by` live on `Object` as real dataclass fields (compare=False to avoid graph-walking `__eq__`). `pIndexData` and `contains` are read+write/read-only `@property` aliases of `prototype` and `contained_items`. (c) `mud/spawning/obj_spawner.py:spawn_object` appends every new instance to `mud.models.obj.object_registry: list[Object]` before returning. `mud/game_loop.py:_extract_obj` removes (recursively via `obj.contained_items`). `tests/conftest.py` autouse fixture snapshots-clears-restores the registry around every test to prevent cross-test leakage. Touched by: `mud/skills/handlers.py` (3 single-arm + 9 tuple-filter isinstance collapses), `mud/game_loop.py` (17 helper retypings + 4 dual-shape fallback deletions), `mud/handler.py` (3 affect-helper retypings), `mud/music/__init__.py`, `mud/ai/__init__.py`, `mud/mob_cmds.py`, 9 test files (35 fixture migrations). | `tests/integration/test_inv012_object_list_canonical.py` | ✅ ENFORCED |
| INV-016 | BCAST-ON-POSITION-TRANSITION | `src/fight.c:damage` is the canonical damage funnel. After it applies the hp delta and calls `update_pos` (handler.c:1380), it `act()`-broadcasts the position-change line per `src/fight.c:837-861` — "X is mortally wounded", "X is incapacitated", "X is stunned", "X is DEAD!!" Every ROM damage path (combat hits, spells, breath weapons, traps) routes through `damage()`, so the broadcast is the natural consequence of any hp drop that crosses a threshold. | (a) `mud/combat/engine.py:apply_damage` (the proper funnel, used by combat) calls `_position_change_message` → `_broadcast_pos_change` after `update_pos` — matches ROM exactly. (b) **Broken**: `mud/skills/handlers.py` damage spells (~18 sites: acid_blast, acid_breath, fire_breath, fire_breath, frost_breath, gas_breath, lightning_bolt, lightning_breath, magic_missile, harm, dispel_evil, dispel_good, energy_drain, color_spray, cause_serious, cause_critical, cause_light, plus future additions) do `target.hit -= damage; update_pos(target)` directly — they bypass `apply_damage`, so spell-induced INCAP/MORTAL/DEAD transitions are silent to the room. ROM does broadcast these (spells go through `damage()` in `src/magic.c`). Sibling of INV-001 SINGLE-DELIVERY but inverted — *zero-delivery*. Touched by: every damage spell handler in `mud/skills/handlers.py` (closing the gap requires either routing through `apply_damage` or factoring `_position_change_message` out for direct invocation). | `tests/integration/test_inv016_position_transition_broadcast.py` (xfail strict — flip to passing when the routing fix lands) | ❌ BROKEN |
| INV-015 | AFFECT-TICK-LIFECYCLE | `src/update.c:762-786 affect_update` decrements every `ch->affected` entry's duration. On expiry it calls `src/handler.c:1317 affect_remove`, which `affect_modify(ch, paf, FALSE)` (subtracts the stat modifier AND clears the bitvector in `affected_by`/`imm_flags`/`res_flags`/`vuln_flags`) → unlinks from `ch->affected` → `affect_check(ch, where, vector)` re-sets the bit only if another affect on `ch` or equipped objects still provides it. The contract: every expired affect that carried a stat mod via `affect_modify(TRUE)` must have it subtracted, and every bitvector it OR'd in must be reconsidered against remaining affects. | (a) `mud/handler.py:affect_remove(ch, paf)` mirrors `src/handler.c:1317` exactly — `affect_modify(False)` → `affected.remove(paf)` → `affect_check(where, vector)`. (b) `mud/affects/engine.py:tick_spell_effects` expiry branch routes ROM-canonical `AffectData` (integer `type`, no parallel `spell_effects` entry) through `affect_remove`. **Spell-effects-managed entries** (the `Character.apply_spell_effect` shadow-mirror path used by frenzy / bless / weaken / etc.) keep bare `affected.remove` — `remove_spell_effect` already runs `_apply_stat_modifier(-mod)` and `remove_affect(bitvector)`, so routing them through `affect_remove` would double-unwind (caught during 2.9.7 implementation by `tests/integration/test_spell_affects_persistence.py::TestSpellAffectPersistence::test_spell_affect_expires_after_duration` + `test_multi_entry_spell_wears_off_once_through_game_tick` + `tests/test_affects.py::test_affect_to_char_applies_stat_modifiers` regressions, hence the explicit split). Touched by: `mud/affects/engine.py:tick_spell_effects`, `mud/handler.py:affect_remove`. | `tests/integration/test_inv015_affect_tick_lifecycle.py` | ✅ ENFORCED |
| INV-014 | OBJECT-REGISTRY-MEMBERSHIP | `src/db.c:create_object` appends every freshly built `OBJ_DATA` to the global `object_list` unconditionally — every world-scan consumer (`src/magic.c:3737 spell_locate_object`, decay sweep, save) iterates that list, so any obj built without registration is invisible to the world. | (a) `mud/models/object.py:create_object(prototype, *, instance_id=None) -> Object` is the canonical Python factory: it constructs the `Object` and appends to `mud.models.obj.object_registry`. (b) Every direct `Object(...)` construction site in production routes through it — `mud/spawning/obj_spawner.py:spawn_object` (inline append, pre-existing), `mud/handler.py:create_money`, `mud/combat/death.py:_fallback_gore`, `mud/combat/death.py:_fallback_corpse`, `mud/rom_api.py:recursive_clone`, `mud/commands/shop.py:_clone_inventory_object` (fallback path when `spawn_object` returns `None`), `mud/models/conversion.py:load_objects_for_character` (DB-restored inventory). (c) `mud/skills/handlers.py:_iterate_world_objects` walks `object_registry` first (computing the holder per ROM `src/magic.c:3747` — outermost `in_obj` chain, then prefer `carried_by` over `in_room`); a legacy room/character secondary walk remains as a compat backstop for unit tests that build `Object` directly without registering. The symptom that surfaced this: `locate object` could not find a freshly-created corpse, money pile, or shop-clone item because those bypassed the registry. | `tests/integration/test_inv014_object_registry_membership.py` | ✅ ENFORCED |

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

**Open: none right now.**

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

**16 of ~20 budget. INV-001 … INV-015 ✅ ENFORCED; INV-016 ❌ BROKEN (documented, fix queued).**

This tracker is small on purpose. If it grows past ~20 invariants,
something has gone wrong with the per-file audit methodology and the
two trackers should be merged or restructured. Discuss before adding
INV-021.
