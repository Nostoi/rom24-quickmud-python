# Differential Harness — Findings

Divergences the harness has surfaced between the Python port and the ROM C
reference. Each is recorded here durably (per AGENTS.md "file durably, don't just
mention") and gated as a `KNOWN_DIVERGENCES` entry in
`tests/test_differential_smoke.py` (an `xfail` that auto-clears when the diff
goes clean). Resolving the root cause is separate from building the harness.

---

## FINDING-027 — money object vnum swap + `create_money` fabricated-proto wording/cost — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-04 (2.13.11). Surfaced by the new deterministic
`money_drop_get_give` scenario (`__silver=200; __gold=10; drop 50 silver; drop 3
gold; get coins; give 25 silver wizard; ...`), which diffs coin-object handling
against the ROM C engine. Two independent engine divergences plus one harness
inconsistency.

**Root cause 1 — vnum constants swapped.** `mud/models/constants.py` defined
`OBJ_VNUM_SILVER_SOME = 3` / `OBJ_VNUM_GOLD_SOME = 4`, but ROM `src/merc.h:1022-1023`
is `OBJ_VNUM_GOLD_SOME 3` / `OBJ_VNUM_SILVER_SOME 4`. `drop 50 silver` therefore
produced a coin object with vnum 3 where the C golden had vnum 4. All consumers
(`create_money`, `do_drop`/`get coins` aggregation in `inventory.py`,
`test_money_objects.py`) reference the symbolic constants, so flipping the two
values is transparent and corrects the wire vnum.

**Root cause 2 — `create_money` fabricated its own proto wording/cost.** ROM
`src/handler.c:2438-2480 create_money` does `create_object(get_obj_index(VNUM))`
and uses the limbo.are #1-#5 prototype's `short_descr` as a printf format
(`sprintf(buf, obj->short_descr, ...)`). The Python port hand-rolled the strings
and economics, diverging:
- one-coin short_descr `"one silver coin"`/`"one gold coin"` vs ROM `"a silver
  coin"`/`"a gold coin"` (limbo.are #1/#2), and cost 1/100 vs ROM proto cost 0;
- mixed-coins `"N silver and N gold coins"` vs ROM `"N silver coins and N gold
  coins"` (limbo.are #5, note the first "coins") — the actual step-8 `get coins`
  diff;
- gold-some `cost = 100 * gold` vs ROM `obj->cost = gold` (`handler.c:2454`).

**Fix:** `mud/handler.py:create_money` now fabricates a per-call `ObjIndex`
mirroring limbo.are #1-#5 (name keywords incl. `gcash`, ROM short_descr wording,
description, value, weight) with ROM's per-branch value/cost/weight from
`handler.c:2438-2480`. A per-call proto (not the shared registry proto) is
required because Python reads object weight from `prototype.weight`
(`inventory.py:_get_obj_weight`), so each coin object needs its own weight. The
ONE branches keep the proto untouched (value[0]/[1]=1, cost 0, weight 10); only
SOME/COINS override. `test_money_objects.py` assertions that encoded the old
port behavior (`"one silver coin"`, cost 100/2500, `"N silver and N gold coins"`)
were corrected to ROM with source citations.

**Harness note (not an engine divergence):** the scenario also exposed that the
Python replay's `__mload` auto-added every spawned mob to the snapshot set, while
the C shim snapshots only `watch.chars` (`diffmain.c` resolves keys strictly from
the declared watch set). `tools/diff_harness/pyreplay.py:__mload` now registers
the mob only when its key is in `watch.chars`, matching C — `combat_melee_rounds`
(which declares `drunk`) is unaffected; the undeclared give-target `wizard` is no
longer snapshotted. Also added `silver` to the snapshot (`schema.py`/`pysnap.py`/
`diffmain.c`) and `__gold=`/`__silver=` replay meta-commands.

**Regression:** `tools/diff_harness/scenarios/money_drop_get_give.json` +
`tests/data/golden/diff/money_drop_get_give.golden.json` lock the C/Python
replay; `tests/integration/test_money_objects.py` (30 cases) covers
`create_money` per branch.

**Outstanding (separate, not exercised):** ROM `create_money` clamps invalid
input (`gold = UMAX(1, gold)`) and never returns NULL; the Python port still
returns `None` and callers guard on it. Left as-is (changing it touches the
`make_corpse`/`do_drop` caller contract); noted here for a future gap.

---

## FINDING-026 — shop sell/value duplicate-stock pricing + ROM act wording — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03 (2.13.9). Surfaced by deterministic
diff-harness widening while adding `shop_sell_weapon` (`list; __oload=3028; get
staff; value staff; sell staff`). The C golden quoted the oloaded wooden staff
at **116 coins** (`16 silver and 1 gold`) while Python quoted **174 coins**.
The same step also exposed two output-format divergences: Python returned
lowercase keeper speech (`the weaponsmith...`) and put the period inside the
quoted `$p` phrase, while ROM `act()` first-letter-capitalizes the line and uses
the literal `src/act_obj.c:3011-3015` punctuation:
`"$n tells you 'I'll give you ... for $p'."`

**Root cause:** `mud/commands/shop.py:_get_cost` attempted to mirror ROM
`src/act_obj.c:get_cost`, but its duplicate-stock discount checked
`op.extra_flags` (the prototype) instead of the keeper's carried object flags.
Reset shop inventory uses carried `Object` instances; an `ITEM_INVENTORY` stock
copy therefore failed the ROM `IS_OBJ_STAT(obj2, ITEM_INVENTORY)` branch and
used the 3/4 non-inventory duplicate discount instead of `/ 2`. `do_value`
also bypassed ROM `act_new` capitalization, and `do_sell` had a Python-invented
zero-gold wording branch plus singular/plural based on `gold == 1` instead of
ROM's `cost == 1`.

**Fix:** `_get_cost` now combines carried-object and prototype extra flags for
the duplicate-stock check, preserving the existing prototype-backed fixture
convention for item type/cost/charge values. `do_value` now formats the ROM
`act()` line with `capitalize_act_line`, sets `reply`, and preserves the quote
punctuation. `do_sell` always emits ROM's
`You sell $p for %d silver and %d gold piece%s.` shape, with the suffix keyed to
the total cost exactly as ROM does.

**Regression:** `tools/diff_harness/scenarios/shop_sell_weapon.json` +
`tests/data/golden/diff/shop_sell_weapon.golden.json` lock the C/Python replay.
`tests/test_shops.py` expectations for zero-gold sell output, duplicate wand
discount compounding, and keeper value speech were updated to the ROM source.

---

## FINDING-024 — save/load discards inventory↔equipment carry-list ordering — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03 (2.13.7). Surfaced while closing the runtime FINDING-020.
The DB save format (`mud/account/account_manager.py`) serializes carried items as
an ordered `inventory_state` list but equipped items as a separate
`equipment_state` **dict keyed by wear slot** — with no record of an equipped
object's position relative to the carried list. On reload
(`mud/models/character.py from_orm`), `inventory` is restored in order but
equipped objects land in the dict with no `_carry_seq` (it defaults to 0 and is
not persisted). A reloaded-then-removed item therefore falls through
`_remove_obj`'s defensive tail-append, losing the ROM-preserved position that
FINDING-020 now reproduces at runtime.

ROM's pfile keeps equipped objects inline in the carry list with `wear_loc`, so
their order survives the round-trip for free. Two faithful fixes: (a) persist
`_carry_seq` per object and re-derive ordering on load, or (b) restore the carry
list inline (re-equip in carry-list order). Distinct from FINDING-020 (runtime,
now closed) — this is the *persistence* leg of the same divergence. Not yet
exercised by the diff harness (the diffshim has no save/reload step). File a
diff-harness save/reload scenario or a focused persistence test when closing.

**Fix:** `ObjectSave` now persists `carry_seq`, `_serialize_object` writes
`Object._carry_seq`, `_deserialize_object` restores it, and `from_orm` advances
the runtime carry-sequence counter past the highest restored value so future
acquisitions sort newer than loaded objects. Regression:
`tests/integration/test_db_canonical_round_trip.py::test_db_round_trip_preserves_equipped_item_carry_position_after_remove`
uses the focused save/load boundary: bag acquired first, sword acquired/equipped
second, jacket acquired after reload; removing the sword after DB round-trip must
produce `[3045, 3021, 3032]`, matching ROM's inline pfile carry-list order.

---

## FINDING-025 — `MobInstance.equip` uses carry-list + `wear_loc` but wield lookups missed it — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03 (2.13.8). Surfaced while closing FINDING-020
(PC carry-list position). `MobInstance.equip` keeps the equipped item **in**
`self.inventory` (via `add_to_inventory`, head-insert) and sets `obj.wear_loc`,
but does not populate a PC-style `equipment` dict. On ROM re-read this
representation is actually the faithful one: ROM uses one carry-list+`wear_loc`
model for mobs and PCs alike (`equip_char` sets `obj->wear_loc`; `get_eq_char`
loops `ch->carrying` at `src/handler.c:1733`).

**Root divergence:** Python's shared `get_wielded_weapon` only checked
`wielded_weapon` and the PC `equipment[int(WEAR_WIELD)]` dict. A reset-equipped
mob therefore looked unarmed to disarm/combat consumers even though it had the
weapon in `inventory` with `wear_loc == WEAR_WIELD`.

**Fix:** `get_wielded_weapon` now falls back to scanning `inventory` for
`wear_loc == WearLocation.WIELD`, matching ROM `get_eq_char`. `MobInstance
.remove_object` clears the carrier back-pointer and `wear_loc`, matching
`obj_from_char`. `disarm` now also mirrors ROM `src/fight.c:2257-2265`: NODROP/
INVENTORY weapons route back through the victim's carry-list, and after dropping
a normal weapon into the room, an NPC victim with `wait == 0` that can see the
weapon immediately picks it back up via `add_to_inventory`.

**Regression:** `tests/integration/test_finding025_mob_equip_disarm.py` covers
the mob `wear_loc` lookup, the NPC disarm auto-reclaim path, and the mob NODROP
carry-list branch. The mob equipment representation is now treated as
intentional/ROM-faithful rather than requiring a dict entry.

---

## FINDING-017 — `Character.add_object` appends to inventory; ROM `obj_to_char` prepends — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03 (v2.13.1). `Character.add_object` now
head-inserts (`self.inventory.insert(0, obj)`), matching ROM `obj_to_char`, and
the contract is tracked as **INV-039 (OBJECT-LIST-HEAD-INSERT)** — which also
covers the two sibling legs found in the same session, **FINDING-018**
(`Room.add_object` / `obj_to_room`) and **FINDING-019** (`_obj_to_obj` /
`obj_to_obj`). Regressions:
`tests/integration/test_inv013_add_object_carrier.py::test_add_object_head_inserts_lifo`
and the three `tests/test_diff_harness_generated.py` order tests
(`..._container_round_trip_...`, `..._room_drop_order_...`,
`..._container_contents_order_...`). Two tests asserted the old append order and
were corrected to ROM LIFO (`test_do_inventory.py::test_inventory_duplicate_order_is_rom_lifo`,
`test_shops.py::test_sell_numbered_selector`). The full suite is green. **Scope
note:** INV-039 covers the three `obj_to_{char,room,obj}` *chokepoints* only;
~25 bypass `append` sites remain (many are order-preserving restore/clone/serialize
paths that must NOT flip) — filed as a `DIVERGENCE_CLASS_ROSTER` sweep, not closed
here.

Surfaced by Phase C generated differential coverage while adding a container
(bag `3032`) round-trip. Minimal sequence:

```
__oload=3032
__oload=3021
get bag
get sword
```

Symptom (step 4 `get sword`):
```
chars[Tester].inventory · C=[3021, 3032] py=[3032, 3021]
```

ROM `src/handler.c obj_to_char` inserts at the **head** of `ch->carrying`
(`obj->next_content = ch->carrying; ch->carrying = obj;`), so the carry list is
LIFO — the most recently acquired object is first. The C snapshot iterates
`ch->carrying` and emits `[sword, bag]` (sword acquired last).

**Root cause:** `mud/models/character.py::Character.add_object` does
`self.inventory.append(obj)` — appends to the tail — even though its own comment
claims `# mirroring ROM src/handler.c:1626 obj_to_char`. Every Python
inventory-acquire path routes through `add_object` (get, get-from-container,
give, buy, steal, auto-loot, outfit, spell-created objects), so all of them
diverge from ROM's head-insert.

**Blast radius:** `gitnexus_impact(add_object, upstream)` → **CRITICAL**, 20
impacted symbols, 8 direct callers (`do_give`, `_get_obj`/`do_get`, `do_buy`,
`_steal_item`, `_auto_collect_loot`, `give_school_outfit`, `create_rose`,
`floating_disc`). Inventory ordering is observable via `do_inventory` listing,
`get all` / `drop all` / `sacrifice` iteration order, and `get <name>` /
keyword-match first-hit selection.

**Fix direction:** make `add_object` head-insert (`self.inventory.insert(0, obj)`)
to match `obj_to_char`, then repair any test that asserted the old append order
(those tests assert non-ROM behavior — AGENTS.md: a test contradicting ROM is a
test bug). The contract spans every acquire path and every iteration consumer,
so it is a candidate cross-file invariant (carry-list head-insert / LIFO).

---

## FINDING-018 — `Room.add_object` appends; ROM `obj_to_room` head-inserts — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03 (v2.13.1). Sibling of FINDING-017, same class
(INV-039). Surfaced by the generated machine: `__oload=3032; __oload=3021; north;
south` then `look` listed room contents in opposite order to ROM. ROM
`src/handler.c:1953 obj_to_room` head-inserts (`obj->next_content =
pRoomIndex->contents; pRoomIndex->contents = obj;`), so room contents are LIFO and
`do_look` lists the most-recently-dropped/loaded object first. `Room.add_object`
appended; fixed to `self.contents.insert(0, obj)`. Note the snapshot
`room.contents` field is SORTED, so this was caught only via the order-preserved
`look` **output**. Regression:
`tests/test_diff_harness_generated.py::test_generated_room_drop_order_matches_live_c`.

---

## FINDING-019 — `_obj_to_obj` appends; ROM `obj_to_obj` head-inserts — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03 (v2.13.1). Sibling of FINDING-017, same class
(INV-039). Source-confirmed (not initially harness-observable — no container-contents
snapshot field). ROM `src/handler.c:1968 obj_to_obj` head-inserts into
`obj_to->contains`, so a container's contents are LIFO. `mud/commands/obj_manipulation.py::_obj_to_obj`
appended to `contained_items`; fixed to `insert(0, obj)`. Guarded by
`tests/test_diff_harness_generated.py::test_generated_container_contents_order_matches_live_c`
(two items put into a bag, order observed via `get all bag` against the live C
oracle — `look in bag` was avoided because it independently trips FINDING-021).

---

## FINDING-020 — `remove` re-appends to inventory, losing ROM's preserved carry-list position — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03 (2.13.6). Distinct from the INV-039 head-insert
class — this is the **equipment-storage architecture** divergence. ROM keeps
equipped objects in `ch->carrying` with only `wear_loc` set (`get_eq_char` loops
the carry list); removing an item (`unequip_char`) merely clears `wear_loc`, so
the object keeps its original carry-list position. The Python port stores equipped
objects in a separate `char.equipment` dict (removed from `inventory` on equip)
and historically re-**appended** them to `inventory` on remove
(`obj_manipulation._remove_obj`), so a removed item landed at the tail regardless
of its original position.

**ROM ground truth (captured from the diffshim C oracle) — position is RELATIVE
to acquisition order, not a fixed index and not always head/tail:**
```
findings_case      get bag; get sword; wield sword; remove sword
  sword acquired AFTER bag  → C inv=[3021, 3032]   (sword in front of bag)
interleave_case    get sword; wield; get bag; get jacket; remove sword
  sword acquired FIRST       → C inv=[3045, 3032, 3021]  (sword at tail)
container_roundtrip put sword bag; get sword bag (re-acquire); wield; remove
  re-acquisition refreshes   → C inv=[3021, 3045, 3032]  (sword back at head)
```
This killed the "store an absolute index and re-insert" approach: there is no
fixed index — new acquisitions head-insert *in front of* an equipped object while
it stays put, so its final slot is determined by acquisition order relative to
items that come and go.

**Fix (acquisition-sequence shim — behaviorally isomorphic to ROM's single carry
list, keeps the enforced `char.equipment` dict convention intact):** a global
monotonic counter stamps `Object._carry_seq` at every carry-list entry
(`Character.add_object`; `equip_object`'s direct-equip else-branch). On unequip,
`_remove_obj` re-inserts the object ahead of the first carried object acquired
earlier than it (lower `_carry_seq`) instead of appending. ROM's `ch->carrying`
is always in descending-acquisition order (only ops are head-insert and remove,
both order-preserving), so a per-object seq + ordered re-insert reproduces every
observable. Verified: Python now matches the C oracle for inventory **and**
equipment across all three cases above plus two-equip, re-equip, and drop-mix
scenarios; the generated state machine's `remove` rules are un-gated (the
`_no_other_carried()` restriction removed) so Hypothesis exercises the formerly-
divergent remove-with-other-carried path against the live C oracle.

**Test:** `tests/integration/test_finding020_equip_remove_carry_position.py`
(3 C-confirmed scenarios) + un-gated `tools/diff_harness/generated.py` remove rules.

**Scope:** resolved for the **PC carry-list path** (`Character.add_object` /
`equip_object` / `_remove_obj`), validated against a PC "Tester". Mobs use a
*separate* equipment representation (`MobInstance.equip` keeps the item in
`inventory` with `wear_loc` set and does not populate the equipment dict) — mob
disarm/remove position is **not** verified by this fix and is filed as the open
**FINDING-025** below. Do not read this RESOLVED as covering mob equipment.

**Out-of-scope follow-up (filed):** save/load discards the inventory↔equipment
ordering relationship in *both* the old and new models — `equipment_state` is a
dict with no position relative to the ordered `inventory_state`, so a
reloaded-then-removed item appends (its `_carry_seq` is 0 / not persisted). The
runtime FINDING-020 is closed; this reload-ordering gap is a distinct concern
tracked as **FINDING-024** below.

---

## FINDING-021 — `look in <container>` header is not first-letter capitalized — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03. ROM renders the container-contents view via
two unconditional steps (`src/act_info.c:1166-1167`):
```c
act ("$p holds:", ch, obj, NULL, TO_CHAR);    /* header — act-capitalized */
show_list_to_char (obj->contains, ch, TRUE, TRUE);
```
`act_new`'s first-visible-char cap (INV-029 / ACT-CAP) yields `A bag holds:`. The
Python `_look_in` CONTAINER branch (`mud/world/look.py`) emitted `a bag holds:`
(lowercase header). Fixed by routing the header through `capitalize_act_line`.

Reading the ROM block to fix the header surfaced an adjacent divergence in the
**same branch**: Python had invented a `"{short} is empty."` branch for empty
containers, but ROM has no such branch — `show_list_to_char` with
`fShowNothing == TRUE` and `nShow == 0` prints `Nothing.` (`act_info.c:227-231`).
So ROM yields `A bag holds:` + `Nothing.` for an empty container. Fixed in the
same commit (one root cause: the branch was a Python invention rather than a port
of the ROM block). The drink-con `"It is empty."` path (`act_info.c:1143`) is
**correct ROM** and was left untouched.

**Test:** `tests/integration/test_finding021_look_in_container_header.py`
(capitalized header + empty-container `Nothing.`).

---

## FINDING-022 — `look in <container>` contents lines carry a 2-space indent ROM omits for a PC — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03. ROM `show_list_to_char` (`src/act_info.c:130-243`) has two
formatting paths: NPC/COMM_COMBINE viewers see 5-space padding (single items) or `(N) `
count prefix (duplicates); non-COMBINE PCs see each item on its own line with **no**
leading indent. The Python `_look_in` container branch (`mud/world/look.py`) was
prepending a fixed 2-space indent (`f"  {item_name}"`), matching neither the
no-indent PC path nor the 5-space COMBINE path.

**Fix:** ported `show_list_to_char` and `format_obj_to_char` from ROM
(`src/act_info.c:87-243`) into `mud/utils/act.py` as shared utilities. The
`_look_in` container branch now calls `show_list_to_char(contents, char,
f_short=True, f_show_nothing=True)` instead of a hand-rolled loop, producing
the correct no-indent output for non-COMBINE PCs and 5-space/(N) output for
COMBINE/NPC viewers. Also includes the `format_obj_to_char` aura-prefix logic
(Invis/Red Aura/Blue Aura/Magical/Glowing/Humming) and `can_see_object`/`WEAR_NONE`
filtering, matching ROM's full `show_list_to_char` behavior.

**Scope note:** the existing `_show_inventory_list` in
`mud/commands/inventory.py` (called by `do_inventory`) replicates the same
COMBINE logic independently; both now agree on behavior. A future refactor
could unify them to call the shared `show_list_to_char`, but that is not
required for this fix.

**Test:** `tests/integration/test_finding022_show_list_to_char_parity.py`
(7 unit tests for `show_list_to_char` + 4 end-to-end tests for `look in`).

## FINDING-023 — `fire_effect` burn-drop silently drops items on the floor (4 sites) — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03 (v2.13.3). Four branches in `mud/skills/handlers.py:_fire_effect`
used `room.objects.append(obj)`, but `Room` has no `objects` attribute — only
`contents`. The `hasattr(room, "objects")` guard always returned `False`, so
items disarmed/dropped by fire (ARMOR, CLOTHING left on body; WEAPON, LIGHT from
inventory) never reached the room. All four sites now route through `room.add_object(obj)`,
which head-inserts (INV-039). Affected: armor burn-drop (line ~5200), clothing
burn-drop (line ~5229), weapon burn-drop (line ~5273), weapon-in-inventory
burn-drop (line ~5300). Regression: `test_spell_heat_metal_rom_parity.py` now
uses `room.contents` (the correct attribute).

## FINDING-024 — class-13 bypass sweep: 15 runtime-placement `.append` sites bypass the INV-039 head-insert chokepoints — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03 (v2.13.3). Systematic sweep of all production `append`
sites placing objects into `inventory`/`contents`/`contained_items`. 15 sites that
should head-insert (ROM `obj_to_char`/`obj_to_room`/`obj_to_obj` all head-insert
their target list) were bypassing the three canonical chokepoints fixed by INV-039:

**Canonical functions fixed to head-insert (`insert(0)`) or route through chokepoint:**
- `game_loop.py:_obj_to_obj` — was `append`, now `insert(0)`
- `game_loop.py:_obj_to_char` — was `append`, now routes through `add_object`/`add_to_inventory`
- `game_loop.py:_obj_to_room` — was fallback `append`, now always `room.add_object(obj)`
- `spawning/templates.py:MobInstance.add_to_inventory` — was `append`, now `insert(0)`
- `spawning/templates.py:ObjectInstance.move_to_room` — was `append`, now `room.add_object`
- `commands/equipment.py:_perform_remove` — was manual `append`, now routes through `add_object`
- `combat/death.py:_handle_corpse_item` — was `append`, now `insert(0)` (corpse items LIFO)
- `combat/death.py:make_corpse` money — was `append`, now `insert(0)`
- `mobs/scavenger` (spec_funs + ai) — now route through `add_object`/`add_to_inventory`
- `mob_cmds.mpoload` fallback — now `insert(0)` + routes through `add_to_inventory`
- `mob_cmds.mptransfer_obj` fallback — now `insert(0)`
- `commands/imm_load` — routes through `add_object`/`add_to_inventory`
- `commands/imm_search` — routes through `add_object`/`add_to_inventory`
- `commands/shop` sell-to-keeper fallback — routes through `add_to_inventory`
- `spawning/reset_handler` container-put — `insert(0)` (reset-area LIFO parity)
- `commands/build:cmd_redit` container-put — `insert(0)`

**Correctly left as `append` (order-preserving reconstruction paths):**
- `db/serializers.py:_deserialize_object` — DB reload, preserves save order
- `models/object.py:recursive_clone` — clones source LIFO order, append yields same result
- `models/conversion.py:load_objects_for_character` — DB reload
- `mob_cmds.do_mpjunk` — filtered inventory rebuild, not object placement
- `object_registry.append(obj)` — global object list, not a placement list

**Dead code removed (fallback `hasattr(room, "objects")` / `hasattr(room, "add_object")`
branches that could never execute because `Room` always has `add_object` and
has no `objects` attribute):**
- `spec_funs._drop_object_into_room` fallback
- `game_loop._obj_to_room` fallback

**Separate finding (filed during sweep):** FINDING-023 (`room.objects` in fire_effect).

**Status:** ⚠️ OPEN 2026-06-03. Surfaced while reading `show_list_to_char`
(`src/act_info.c:130-243`) to fix FINDING-021. For a non-NPC char **without**
`COMM_COMBINE`, ROM adds **no** leading indent to each listed object — the indent
block (`     ` 5-space pad, or `(%2d) ` count) is gated on `IS_NPC (ch) ||
IS_SET (ch->comm, COMM_COMBINE)` (`act_info.c:210-221`). The Python `_look_in`
CONTAINER branch prepends a fixed 2-space indent (`f"  {item_name}"`), which
matches neither the no-indent PC path nor the 5-space COMBINE path.

Not yet confirmed against the live C oracle (the generated machine still avoids
`look in` for the contents lines — only the header was hand-observed). Left out of
the FINDING-021 fix to keep that commit atomic; the documented FINDING-021 note
said contents "match", so this needs an oracle run before fixing. A faithful fix
also implies porting `show_list_to_char`'s combine/count semantics for PCs with
`COMM_COMBINE`, so scope it deliberately. Filed for follow-up.

---

## FINDING-016 — `remove` left stale `worn_by`, blocking re-wear after armor removal — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-06-03. Surfaced by Phase C generated differential
coverage after adding `__oload` object lifecycle rules. The minimal Hypothesis
sequence was:

```
__oload=3045
get jacket
wear jacket
remove jacket
wear jacket
```

Symptom (step 5):
```
C : ['You wear a scale mail jacket on your torso.']
py: ['You are already wearing that.']
```

**Root cause:** `mud.commands.obj_manipulation._remove_obj` removed the object
from `char.equipment` and reset `obj.wear_loc` via `unequip_char`, but did not
clear the Python-only `obj.worn_by` back-pointer. `do_wear` checks
`obj.worn_by is ch` before dispatching wear logic, so a removed item still looked
equipped even though `wear_loc == WEAR_NONE` and it was back in inventory. ROM
has no separate `worn_by`; `unequip_char` leaves the object carried by the
character and sets only `wear_loc = WEAR_NONE`, so re-wear succeeds.

**Fix:** `_remove_obj` now clears `obj.worn_by = None` after `unequip_char`, and
the equipment-dict removal loop uses identity (`is`) instead of value equality,
matching ROM pointer semantics. Regression:
`tests/integration/test_remove_command.py::test_do_remove_happy_path_emits_both_messages`
now asserts the stale pointer is cleared and the item can be worn again. The
generated live C/Python test also converges.

**Instrumentation note:** the same widening added `__oload=<vnum>` to both the C
shim (`create_object` + `obj_to_room`) and Python replay (`spawn_object` +
`Room.add_object`). While triaging this finding, the C snapshot's inventory field
was tightened to carried, non-equipped objects; equipped objects are compared
through the existing `equipment` field.

---

## FINDING-015 — affect spells emit no ROM success message when cast through `do_cast` — ✅ RESOLVED (armor; bless/shield sweep open)

**Status:** ✅ RESOLVED 2026-05-29 (master v2.11.20, `a3476e33`) — the `armor` handler now
delivers ROM's success messaging, so `affect_armor` converges end-to-end and the
`KNOWN_DIVERGENCES` entry self-cleared. Surfaced by the new `affect_armor` scenario (an L10
mage self-casts `armor`). The broader bless/shield/… sweep remains open under
`docs/parity/MAGIC_C_AUDIT.md` **MAGIC-002**.

**Scenario:** `affect_armor` — `__seed=777`, `__learn=armor`, `cast armor` (level 10 so a
mage clears armor's `skill_level[mage]==7` gate; armor is −20 AC regardless of level, so the
higher level keeps the baseline clean).

Symptom (step 3, `cast armor`):
```
C : ['You feel someone protecting you.']
py: []
```
Everything else converges: `affects == ['armor']`, `eff_ac == [80,80,80,80]` (−20), and
`mana == 80` (100 − 20) on both sides. The **only** diverging field is `output`.

**Root cause:** ROM `spell_armor` (`src/magic.c:753-777`) sends
`"You feel someone protecting you.\n\r"` to the victim on success (and `act("$N is protected
by your magic.")` to the caster when `ch != victim`). The Python `armor` handler
(`mud/skills/handlers.py:1335`) applies the affect but sends **nothing** on success. Because
`do_cast` is silent on a successful cast (FINDING-013: all player-facing output comes from the
spell function), the message is dropped entirely.

This is a **class**, not a one-off: `bless` (`handlers.py:1465`) and `shield`
(`handlers.py:7094`) are likewise silent on success, so every affect-only spell cast through
`do_cast` is missing its ROM success line. (When cast via the older `skill_registry.cast`
path they instead get the generic `_default_success_message` "You cast <spell>." fallback —
also non-ROM, just a different wrong string.) The `affect_armor` scenario exercises and fixes
the `armor` instance; the broader sweep (bless/shield/giant strength/haste/frenzy/… — verify
each handler against its `src/magic.c` `spell_*` success message) is filed under MAGIC-002 as
follow-up, not closed here (one gap = one test = one commit).

**Fix (armor, on master):** make the `armor` handler deliver ROM's messaging faithfully —
`"You feel someone protecting you."` to the target on success, and the `"$N is protected by
your magic."` caster line for a cross-target cast; also correct the already-affected branch to
ROM's `"You are already armored."` / `act("$N is already armored.")` (Python currently sends
the non-ROM `"They are already protected."`). Regression: a master integration test
(`tests/integration/test_magic_002_armor_message.py`) asserting the success message reaches
the target through `do_cast`; the differential `affect_armor` golden then converges and the
`KNOWN_DIVERGENCES` entry self-clears.

**Instrument note (separate from the bug):** before this scenario the snapshot's `affects`
field was never exercised by any golden, and `pysnap._affect_names` only read
`aff.spell_name`/`aff.name` — neither of which the real affect model (`AffectData`) carries
(it stores the spell identity in `.type`: a lowercase ROM skill name in the SpellEffect-sync
path, or an int SN via `affect_to_char`). So `affects` was silently always `[]` on the Python
side. Fixed in `pysnap.py` (read `.type`, mapping int SNs through `ROM_SKILL_NAMES_BY_INDEX`
to match the C shim's `skill_table[paf->type].name`), locked by two Python-only unit tests in
`test_diff_harness_unit.py`. The `affect_flags` case mismatch (C lowercase `affect_flags[]`
vs Python `AffectFlag.<NAME>.name`) is **not** touched here — `armor` sets no bitvector, so no
flag is exercised; defer that normalization to a flag-setting scenario (sanctuary/haste/
detect-invis) where a real golden can prove it.

---

## FINDING-014 — wait-state ("lag") enforcement: synchronous pulse-loop vs async — ✅ RESOLVED (architectural divergence)

**Status:** ✅ RESOLVED 2026-05-29 as a **documented architectural divergence** (class of
`docs/divergences/MESSAGE_DELIVERY.md`), **not a parity bug** — no production change. The
replay now drives ordinary commands below the wait gate (`char.wait = 0` before
`process_command`), mirroring the C shim's direct `interpret()`. With that, **`spell_combat`
converges end-to-end** (all 7 steps; removed from `KNOWN_DIVERGENCES`).

**Why it is not a bug:** in real ROM you *cannot* cast twice with zero intervening pulses —
`WAIT_STATE` from cast 1 makes the comm.c loop defer cast 2 until `wait` decrements. The C
golden shows both casts firing *only* because the diffshim calls `interpret()` directly,
**bypassing ROM's own comm-loop gate** (`src/comm.c:619-621`/`:820-822`). So the back-to-back
casts are an **instrument artifact, not real ROM behavior** — Python's handler-level wait
enforcement (`do_cast` etc.) is actually the *more* faithful end-state. Two corroborations:
the snapshot schema has **no `wait` field** (wait was never under comparison), and the C side
has wait **set-but-unchecked**; the harness drives *below* the gate on C and *above* it on
Python — that asymmetry *is* the finding. A real input-loop wait gate for Python (like
comm.c, above `process_command`) is a worthwhile *separate* project but would not converge
the differential by itself (the replay must still drive below the gate).

Symptom (step 6, the second consecutive `cast 'magic missile' drunk`, before the replay fix):

Symptom (step 6, the second consecutive `cast 'magic missile' drunk`):
```
C : ['Your magic missile grazes the drunk.']
py: ['You are still recovering.', 'You are still recovering.']
```

**Root cause:** ROM `do_cast` only *sets* wait via `WAIT_STATE(ch, skill_table[sn].beats)`
(`src/magic.c:547`); it never rejects a cast for `ch->wait > 0`. The wait gate lives in
the **game loop** (`src/comm.c:619-621` and `:820-822`): each pulse the loop decrements
`d->character->wait` and skips processing that descriptor's queued input until wait
reaches 0 — the command is *deferred silently*, never rejected, and ROM sends no
"You are still recovering." message. Python instead checks `char.wait > 0` *inside* the
command handlers (`do_cast` `mud/commands/combat.py:827`, plus `do_kick`/`do_rescue`/
`do_backstab`/`do_berserk`/`do_bash` at :178/:236/:349/:402/:537) and returns a synthetic
"You are still recovering." line. So the differential's second cast — driven directly via
`process_command`/`interpret`, bypassing the loop on both sides — is *rejected* in Python
but *executes* in C. (The doubled py line is `do_cast` both `return`-ing and appending the
message to `char.messages`.)

**Optional separate project (not required for parity):** if Python's input model is ever made
to enforce wait at the loop level like ROM `comm.c` (defer input under wait, above
`process_command`), the ~5 in-handler `char.wait > 0` checks (`do_cast`
`mud/commands/combat.py:827`, plus `do_kick`/`do_rescue`/`do_backstab`/`do_berserk`/`do_bash`
at :178/:236/:349/:402/:537) and the synthetic "You are still recovering." message (no ROM
source) would move there. This is an async-architecture improvement, deliberately out of
scope here — the handler-level enforcement is the more faithful behavior today, and the
replay drives below the gate to keep the scenario exercising interpret-level parity.

---

## FINDING-013 — `do_cast` emits a spurious "You cast <spell>." line ROM never sends — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-29 via **master v2.11.19** (`do_cast` now returns `""` on a
successful cast; the spell handler's own message is the only player-facing output, matching
ROM `src/magic.c:553-563`). Merged into `diff-harness`; `spell_combat` step 5 now converges
and the first divergence advanced to **step 6** (FINDING-014). Regression:
`tests/integration/test_finding_013_cast_silent_on_success.py`. Re-baselined
`tests/test_skills_spells_cast_listing.py::test_do_cast_offensive_no_target_defaults_to_fighting_victim`.

Historical (surfaced 2026-05-29 the moment FINDING-012 unblocked casting). Gated in
`KNOWN_DIVERGENCES` until resolved.

**Scenario:** `spell_combat` — an L5 mage `__learn=magic missile` then
`cast 'magic missile' drunk` twice, then one `__tick`.

Symptom (step 5, first cast):
```
C : ['Your magic missile maims the drunk.']
py: ['You cast magic missile.', 'Your magic missile maims the drunk.']
```

**Root cause:** ROM `do_cast` (`src/magic.c:553-563`) is **silent on a successful
cast** — it deducts mana, calls `spell_fun`, and `check_improve`; the only player-
facing output is whatever the spell function itself sends (here `damage()` →
"Your magic missile maims the drunk."). Python's `do_cast`
(`mud/commands/combat.py:897`) and `skill_registry.cast`
(`mud/skills/registry.py:277`) both `return f"You cast {skill.name}."`, and the
command dispatcher sends a command's return value to the player
(`mud/net/connection.py:1979-2000`) — so the player sees an extra confirmation
line ROM never produces.

**Blast radius (why this is not a one-liner):** the `"You cast {skill.name}."`
string is the return contract of both cast entry points and is asserted by 3
existing tests — `tests/test_skills_spells_cast_listing.py:218`,
`tests/test_skills.py:60` & `:118`. The ROM-faithful fix returns `""` on success
(the spell handler already delivers messages via `char.messages`/`_deliver_message`)
and re-baselines those 3 assertions (per AGENTS.md, a test contradicting ROM is the
test's bug). File as a per-file gap before closing.

---

## FINDING-012 — `MobInstance` lacks `saving_throw`, crashing `saves_spell` for any NPC spell target — ✅ RESOLVED (fix applied, pending master land)

**Status:** ✅ Fix applied in the `diff-harness` worktree (`mud/spawning/templates.py`);
**pending commit + land on master**. Surfaced 2026-05-29 by the new `spell_combat`
scenario, step 5 (the first offensive cast at an NPC).

Symptom (step 5, before fix):
```
C : ['Your magic missile maims the drunk.']
py: ["Spell cast failed: 'MobInstance' object has no attribute 'saving_throw'"]
```
(`do_cast` wraps `spell_fun` in try/except, so the `AttributeError` surfaced as a
"Spell cast failed: …" line instead of crashing the process.)

**Root cause:** ROM `CHAR_DATA.saving_throw` is a field shared by PCs **and** NPCs;
`saves_spell` (`src/magic.c:170`) reads `victim->saving_throw` for every target. The
Python `MobInstance` dataclass mirrors many `CHAR_DATA` fields but **omitted
`saving_throw`**, so any `saves_spell`-using offensive spell cast at an NPC raised
`AttributeError`. (No prior test caught it — existing spell tests target PCs or
bypass the NPC-victim `saves_spell` path; the differential exercised it directly.)

**Fix:** added `saving_throw: int = 0` to `MobInstance` (mirrors ROM `create_mobile`,
which leaves a mob's `saving_throw` at 0 — never set from the proto). Purely
additive (new field, default 0; no constructor or reader change). `gitnexus_impact`
= HIGH by import-graph breadth (125 importers) but functionally low-risk (additive).

---

## FINDING-011 — combat miss line drops the attack noun — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-29 via **FIGHT-028** (master v2.11.16). `dam_message`
had a `percent <= 0` early-return that forced the no-noun `TYPE_HIT` template for
*any* miss (and any low-damage hit rounding to percent 0), regardless of `dt`. ROM
`src/fight.c:2157` chooses its template purely on `dt == TYPE_HIT` vs not — `dam == 0`
only swaps `vs/vp` to "miss"/"misses". Deleted the block so the no-noun output keys
solely on `attack is None`; a resolved-noun miss now renders "$n's beating misses you"
like its own hit path. **`combat_melee_rounds` now converges end-to-end** (clean diff,
no xfail) and was removed from `KNOWN_DIVERGENCES`. Regression:
`tests/integration/test_fight_028_miss_attack_noun.py`.

Historical (surfaced 2026-05-29 the moment FINDING-010 (FIGHT-027, v2.11.15) was
closed): with the unarmed-NPC damage-dice fix merged from master, the
`combat_melee_rounds` first divergence advanced from step 6 to **step 7** (the
*third* `__tick`/`violence_update` round); steps 1–6 converged fully on both
engines.

Symptom (step 7, third combat round — the drunk *misses*):
```
step 7 (command='__tick') · output ·
  C  = ["The drunk's beating misses you.", 'You scratch the drunk.']
  py = ["The drunk misses you.",            'You scratch the drunk.']
        └ C includes the attack noun "beating"; py drops it on the miss line
```

Line 2 (the PC's swing) is identical, and the hp converges (both engines: the
drunk's miss deals 0). The only diff is the **miss-line rendering**: ROM
`dam_message` (`src/fight.c:2171-2211`) for `dt != TYPE_HIT` builds
`"{4$n's %s %s you%c{x"` with `attack = attack_table[dt - TYPE_HIT].noun` and
`vp = "misses"` (for `dam == 0`), i.e. **"The drunk's beating misses you."**.
Only the bare `dt == TYPE_HIT` case (`src/fight.c:2157-2169`) renders the
noun-less `"$n %s you"`. The drunk's `dt = TYPE_HIT + 13` ("beating"), so ROM
uses the noun template — and indeed a *hit* by the same mob renders
"The drunk's beating hits you." correctly in Python (step 5/6). So Python's
**miss path** specifically routes through the noun-less template where its own
hit path uses the noun template.

**Root cause (to confirm):** the Python miss path (`apply_damage` with `dam == 0`,
or `mud/combat/messages.py:dam_message`) selects the `TYPE_HIT` noun-less branch
instead of the attack-noun branch keyed on `dt`. Distinct from FIGHT-027 (damage
calc) — this is dam_message rendering. Closed as **FIGHT-028** in
`docs/parity/FIGHT_C_AUDIT.md` (see Status above).

---

## FINDING-010 — combat-tick round-2 damage amount diverges (severity verb) — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-29 via **FIGHT-027** (master v2.11.15). Root cause:
`mud/combat/engine.py:calculate_weapon_damage` had no `IS_NPC` branch, so an
unarmed mob fell through to the **PC-unarmed** formula
`number_range(1 + 4*skill/100, 2*level/3*skill/100)`. For the drunk #3064 (level 2,
damage dice 1d6, skill_total ≈ 50) that collapsed to a degenerate
`number_range(3, 0)` → ROM returns `from` = constant **3**, consuming **zero**
`number_mm` draws — so the Python drunk dealt a constant 3 every hit (round 1's
tier happened to match C's roll of 3), while ROM rolls `dice(1, 6)` (range 1–6,
**one** draw). The round-4 C hit of **5** is unreachable by the old-format
`number_range(level/2, level*3/2)`=1–3, proving the new-format dice path. The
missing draw *also* desynced the shared combat RNG stream from round 2 on. Fix:
`calculate_weapon_damage` now resolves an unarmed NPC (`is_npc and wield is None`)
via `rng_mm.dice(damage[DICE_NUMBER], damage[DICE_TYPE])` (ROM `convert_mobile`
makes `new_format` universal at runtime, so the dice path is the only live one).
**Verified:** the `combat_melee_rounds` differential now converges on all of steps
1–6 (hp + severity verbs match); the first divergence advanced to step 7, filed as
**FINDING-011** (miss-line noun). Regression:
`tests/integration/test_fight_027_npc_unarmed_damage_dice.py`. Historical
investigation notes retained below.

### (historical) original triage

Surfaced 2026-05-29 the moment FINDING-009 (all 4 facets)
was fully closed. With FIGHT-021/022/023/024/025 + the worktree `reversed()`
merged from master, the `combat_melee_rounds` first divergence advanced from
step 5 to **step 6** (the *second* `__tick`/`violence_update` round); **step 5
now converges fully on both engines.**

Symptom (step 6, second combat round):
```
step 6 (command='__tick') · output ·
  C  = ["The drunk's beating scratches you.", 'You scratch the drunk.']
  py = ["The drunk's beating hits you.",      'You scratch the drunk.']
        └ damage SEVERITY differs: C "scratches" (≤5% tier) vs py "hits" (≤15% tier)
```

Line 2 (the PC's swing) is identical. The capitalization ("The"), damtype noun
("beating"), and message order all match — **FINDING-009 facets 1–4 are
confirmed closed end-to-end.** The only diff is the drunk's **damage amount** to
the player landing in a different `_DAMAGE_TIERS` bucket: C deals ≤5% of the
player's `max_hit` (20) ≈ ≤1 dmg → "scratches"; Python deals (5%,15%] ≈ 2–3 dmg
→ "hits".

**Notable:** round 1 (step 5) drunk swing is "beating hits you" in *both*
engines (damage matched), but round 2 (step 6) diverges — so the streams/state
agree for one round and drift by the next.

**Root cause UNKNOWN — including whether this is pre-existing or a regression
introduced by the FINDING-009 fixes. Rule out regression FIRST:** step 6 was
*never compared* before this session (py diverged at step 5), so "pre-existing"
is unproven. FIGHT-023 changed the drunk's damage class SLASH→BASH (reasoned
inert for the differential char — uniform AC `[100,100,100,100]`, no RIV — but
unverified at round 2), and FIGHT-021/022 changed `mob_hit`'s per-round draw set.
Either could shift round-2 damage.

Candidates to probe:
- **Round-2 RNG draw-count residual.** Step-5 convergence proves round *1*, not
  steady state. If draw *counts* diverge by round 2, facet 1 isn't fully closed
  at steady state — OR the inter-round wait/daze burn in `violence_tick`
  diverges from ROM and re-gates `mob_hit`'s `wait==0` checks differently on the
  second round (the FIGHT-022 `number_range(0,2)`/`(0,8)` draws are gated on
  `ch->wait`). The unit tests pin the drunk's *single-round* draw count, so this
  wait-state/round-2 path is the more likely culprit than the count itself.
- **Damage-formula divergence** (damroll / STR damage app / position or AC delta
  between rounds) that round 1's tier happened to mask.

Distinct from FINDING-009's 4 rendering/draw-order facets. `combat_melee_rounds`
stays in `KNOWN_DIVERGENCES` (xfail) under FINDING-010 until round-2 damage
converges. **Discriminating probe:** dump the per-round draw *sequence* +
damage components (dice value, damroll, STR app, RIV, **and the drunk's
wait-state between rounds**) for both engines at step 6. Draw counts diverge →
facet-1/wait-state residual (rule out regression); draws match but damage differs
→ formula bug. File the root cause as a FIGHT-NNN gap once isolated.

---

## FINDING-009 — combat-tick round diverges at `__tick` (violence_update) — ✅ RESOLVED (all 4 facets)

**Status:** ✅ RESOLVED 2026-05-29 — all four facets closed; step 5 (`__tick`)
converges fully on both engines and the first divergence advanced to **step 6**
(round-2 damage amount, now tracked as **FINDING-010**). Surfaced 2026-05-28 the
moment FINDING-008 was fully closed; probed + root-caused into four facets, all
now fixed on master:
- **Facet 1** (`multi_hit`/`mob_hit` RNG draw-count desync) — FIGHT-021 (`79c4d7f7`, v2.11.9) + FIGHT-022 (`4d9fb5c3`, v2.11.10).
- **Facet 2** (mob `dam_type` attack-table index → noun "beating") — FIGHT-023 (`027eee0f`, v2.11.13).
- **Facet 3** (combat-tick iteration order — `violence_tick` reversed) — FIGHT-024 (`863f8734`, v2.11.12).
- **Facet 4** (act() first-char capitalization "The") — FIGHT-025 (`b8878785`, v2.11.14).
- Plus **FIGHT-026** (`850662b5`, v2.11.11) — a latent crash facet 3's reorder exposed (NPC `do_dirt`/`do_trip`/`do_disarm` on `mob_hit` dispatch).

With the step-4 `kill drunk` first strike matching (FIGHT-019 + FIGHT-020 + colour/`fighting`-key
normalization), the `combat_melee_rounds` first divergence advanced to **step 5
`__tick`** — the `violence_update` combat round that resolves both combatants' swings.

Original symptom (Python iterating `character_registry` forward):
```
step 5 (command='__tick') · output ·
  C  = ["The drunk's beating hits you.", 'You miss the drunk.']
  py = ['You scratch the drunk.',        "the drunk's slice hits you."]
```

`__seed=777` ran before step 4, so both engines resolve this round from the same
RNG state. The probe split this into **four facets, each root-caused** (two
empirically, two by ROM source read). **Facets 1 + 3 are now closed**; the remaining
step-5 diff is isolated to line 1 (the drunk's swing rendering — facets 2 + 4):
```
step 5 (command='__tick') · output ·   (after facet-3 reversed() + FIGHT-021 + FIGHT-022)
  C  = ["The drunk's beating hits you.", 'You miss the drunk.']
  py = ["the drunk's slice hits you.",   'You miss the drunk.']
        └ f4: The/the · f2: beating/slice    └ line 2 IDENTICAL — facets 1+3 closed ✓
```

### Facet 3 — message order — ✅ FIXED (master FIGHT-024, v2.11.12)

ROM `violence_update` (`src/fight.c:72`) walks `char_list` **head-first**, and ROM
inserts every new char at the HEAD of `char_list` (`src/db.c:2256-2257`
create_mobile; `src/nanny.c:757-758` PC login) — so the list is in **reverse-creation
order: the most-recently-loaded actor swings first.** The drunk (loaded after Tester)
acts first. Python's `character_registry` is **append-order**, and `violence_tick`
iterated `list(character_registry)` forward → Tester first → reversed message order.

**Fix (staged in worktree, `mud/game_loop.py:violence_tick`):** iterate
`list(reversed(character_registry))` (snapshot guards mid-tick removals, mirroring
ROM's `ch_next = ch->next`). **Verified by re-run:** the message order flipped to
match C — the drunk now swings first. This is load-bearing for RNG draw sequence
(who consumes the stream first), not cosmetics. Belongs on master (combat-tick swing
order changes game-wide → blast radius; grep callers + run full combat integration
suite, triage non-ROM-order assertions as test bugs).

Post-fix diff (swings now aligned, so facets 1/2/4 read independently):
```
  C  = ["The drunk's beating hits you.", 'You miss the drunk.']
  py = ["the drunk's slice hits you.",   'You scratch the drunk.']
        └ drunk swing: hit MATCHES ──┘    └ Tester swing: hit/miss DIFFERS (facet 1)
          only noun (f2) + capital (f4) differ
```

### Facet 1 — `multi_hit`/`mob_hit` RNG draw-count desync — ✅ FIXED (master FIGHT-021 + FIGHT-022)

**Closed 2026-05-28** as two master gap-closers — FIGHT-021 (`commit 79c4d7f7`, v2.11.9)
+ FIGHT-022 (`commit 4d9fb5c3`, v2.11.10). Convergence verified end-to-end: with the
worktree's facet-3 `reversed()` plus both fixes, step-5 line 2 (Tester's swing) now
reads `You miss the drunk.` on both engines (`scratch`→`miss`). Root cause + fix below.

The drunk swings first in both engines and **both hit** ("hits" tier matches), yet
Tester (2nd swing) **misses in C but scratches in Python** — Tester starts its
`one_hit` from a *different RNG stream position* because the drunk's swing consumes a
**different number of draws** in Python. Root cause (read in `mud/combat/engine.py`
`multi_hit` vs ROM `src/fight.c` `multi_hit`/`mob_hit`):

- **(a) Guarded second/third-attack draws.** Python guards the second/third-attack
  `number_percent()` behind `if skill > 0` (`engine.py:346,362`). ROM evaluates
  `number_percent() < chance` **unconditionally** — the draw fires even when
  `chance==0` (a 0-skill attacker). So a no-skill attacker draws 0 in Python, 2 in ROM.
- **(b) No `mob_hit`.** Python's `multi_hit` treats PC and NPC identically. ROM
  `multi_hit` for an NPC calls `mob_hit` and returns — a separate path that (after
  the unconditional 2nd/3rd `number_percent()`) draws `number_range(0,2)` (mob-cast
  check) and `number_range(0,8)` (mob-skill check) when `ch->wait==0`. Python's NPC
  path omits both.

For the drunk (NPC, no second/third skill, `wait==0` on the first `__tick`): **ROM
draws 4 values after `one_hit` (2× `number_percent` + `number_range(0,2)` +
`number_range(0,8)`) that Python draws 0 of** → Python's stream is 4 draws behind
when Tester swings. **Real, broad parity bug** — affects every combat round
game-wide, latent because the suite uses seeded synthetic combat that never compared
against a ROM golden stream. Master gap-closer(s); likely two rows (the unconditional
2nd/3rd draw, and a faithful `mob_hit` port). Note `engine.py` + `game_loop.py` are on
the 32KB gitnexus-gap list — `gitnexus_impact` under-reports; grep + integration suite.

### Facet 2 — mob attack noun ("beating" → "slice") — ✅ FIXED (master FIGHT-023, v2.11.13)

C `beating`, Python `slice`. ROM `ch->dam_type` is an **attack_table index**
(`src/const.c`: index 13 = `{"beating", "beating", DAM_BASH}`, index 0 =
`{"slice","slice",DAM_SLASH}`); the noun is `attack_table[dam_type].noun`
(`src/fight.c:2176`, via `dt = TYPE_HIT + ch->dam_type` for an unarmed mob,
`fight.c:420-424`). Python conflates `dam_type` with a **DamageType damage-class**
(`templates.py:366` `_parse_damage_type`, `:396-403`; `engine.py:403`
`attack_index = attacker.dam_type or 0`), defaulting the index to 0 = "slice". The
`.are` damtype word "beating" is read into `proto.damage_type`
(`mud/loaders/mob_loader.py:152`) but never mapped through an `attack_lookup`. **Real
parity bug** — bigger than cosmetic: the correct index also fixes the damage *class*
(SLASH→BASH), which feeds AC-index and RIV selection. Master gap-closer (verify
`_parse_damage_type` first — confirm whether it string-matches "beating" to anything
and whether `proto.dam_type` is ever set numerically).

### Facet 4 — act() sentence-initial capitalization ("the" → "The") — ✅ FIXED (master FIGHT-025, v2.11.14)

C `The drunk's …`, Python `the drunk's …`. ROM `act_new` (`src/comm.c`) uppercases the
first rendered character (`buf[0] = UPPER(buf[0])`). Python's act/`dam_message` render
path does not. **Real rendering gap.** Fix at Python's single act/`dam_message`
chokepoint (capitalize once — do NOT sprinkle `.capitalize()`). Candidate INV
(act-render contract) or a per-file act row. Master gap-closer.

**Resolved:** all four facets landed on master (FIGHT-021/022/023/024/025, plus the
FIGHT-026 crash fix) and merged into the worktree. Step 5 now converges on both
engines — verified end-to-end via `pytest tests/test_differential_smoke.py -k
combat_melee`. The first divergence advanced to **step 6** (round-2 damage amount),
so `combat_melee_rounds` remains in `KNOWN_DIVERGENCES` (xfail) but now under
**FINDING-010**, not FINDING-009.

---

## FINDING-008 — combat first-attack outcome / message rendering diverges at `kill` — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28. Surfaced the moment FINDING-007 was fixed; the
`combat_melee_rounds` first divergence sat at **step 4 `kill drunk`**
(`C=['You miss the drunk.']` vs `py=['{2You scratch the drunk.{x', '{2You scratch the
drunk.{x']`). All three sub-issues triaged and closed; the differential advanced past
step 4 to **FINDING-009** (step 5).

1. **Hit/miss + damage-tier outcome** — ✅ **real parity bug**, fixed as **FIGHT-019**
   (master 2.11.4). Production combat shipped a non-ROM percent hit model behind a
   `COMBAT_USE_THAC0=False` flag; ROM resolves every swing through the THAC0 /
   `number_bits(5)` roll. Made THAC0 the only path → step-4 first strike is now `miss`
   on both engines. (`docs/parity/FIGHT_C_AUDIT.md` FIGHT-019.)
2. **Color codes** — ✅ **harness normalization** (compare-fairness, like
   FINDING-002/005). The C shim's descriptor runs colour-off (ROM `colour()` non-ANSI
   branch eats every `{X` pair), so its golden is plain text; the Python engine emits
   raw ROM colour tokens. `compare._normalize_output` now applies
   `mud.net.ansi.strip_ansi` (mirrors the ROM non-colour branch) to both sides — a
   no-op on the already-plain C side. Fixed on `diff-harness`.
3. **Double-delivery** — ✅ **real SINGLE-DELIVERY (INV-001) engine bug, fixed as
   FIGHT-020** (master 2.11.5) — **NOT the "harness capture artifact" the earlier
   triage recorded.** `do_kill` returned `multi_hit(...)[0]` — the attacker line
   `apply_damage` had already pushed via `_push_message` — so the connection loop
   double-delivered it to connected PCs (the same class as the WS death-path bug).
   `do_kill` now returns `""`. The sibling `broadcast_room`/`broadcast_global` (2.11.6)
   and `do_surrender` (2.11.7) double-sends were closed in the same INV-001 sweep.
   Closing #3 also surfaced a harness `fighting`-field key mismatch (snapshot recorded
   the mob display name `the drunk` vs the C shim's char_key `drunk`); `pysnap._char_snap`
   now records `fighting` via `_person_key`, matching the room/char key convention.

**Outcome:** step 4 matches byte-for-byte on both engines; the gate moved to
FINDING-009 (the step-5 `__tick` round).

---

## FINDING-007 — mob spawn RNG draw-order diverges (gold vs HP) — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 via **SPAWN-001** (master `47f8fd75`,
v2.11.3). `MobInstance.from_prototype` now draws the spawn RNG stream in ROM
`create_mobile` order — **gold/wealth → HP dice → mana dice → random damtype
(`dam_type == 0`) → random sex (`sex == EITHER`)** — so the drunk #3064 spawns at HP
**31** on both engines from seed 777. Verified end-to-end: the `combat_melee_rounds`
first divergence advanced past the `__mload` spawn step (steps 1–3 now match the C
golden) to the step-4 combat output, which is the separate **FINDING-008**. Regression:
`tests/integration/test_spawn_001_rng_draw_order.py`; audit row
`docs/parity/DB_C_AUDIT.md` SPAWN-001. Original analysis below.

**Status (historical):** 🔴 OPEN — **real Python parity bug.** Surfaced 2026-05-28 by the
`combat_melee_rounds` scenario: the drunk #3064 spawns at HP **31** in ROM C vs **33**
in Python from the *same* seed (777). Both roll the correct `2d6+22` (FINDING-006 is
fixed); the values differ because the two engines draw RNG in a **different order**
during mob creation.

**Root cause.** ROM `create_mobile` (`src/db.c:2047-2091`) draws in this order:
1. **gold/wealth** — `number_range(wealth/2, 3*wealth/2)` then `number_range(wealth/200, wealth/100)` (2 draws when `wealth > 0`),
2. **HP** dice, 3. **mana** dice, 4. random damtype via `number_range(1,3)` *only if* `dam_type == 0`.

Python `MobInstance.from_prototype` (`mud/spawning/templates.py:364-394`) draws:
1. random damtype (`number_range(1,3)`) *first* if `dam_type == 0`,
2. **HP**, 3. **mana**, 4. **gold** *last*.

So gold is drawn last in Python but first in ROM, and the damtype roll is first vs
last. The drunk has `wealth=65 > 0`, so ROM's 2 gold draws precede its HP roll while
Python's don't — shifting the `2d6`. This affects **every seed-dependent mob spawn**
game-wide (mob stats diverge from ROM), latent because the suite uses synthetic mobs.

**Fix shape (master gap-closer, e.g. SPAWN-001 / a templates.py row):** reorder
`from_prototype`'s RNG draws to match `create_mobile` exactly — gold/wealth first, then
HP, then mana, then the `dam_type == 0` random roll last. Bounded to one function;
expect possible seeded-test fallout (it changes spawn RNG order). Same pattern as
DB2-007: a real Python parity bug surfaced by the harness, fixed on master, then
re-run the differential (the `combat_melee_rounds` `KNOWN_DIVERGENCES` xfail
auto-clears when the diff goes clean).

**Gated:** `combat_melee_rounds` is in `KNOWN_DIVERGENCES` (xfail) until this lands.

---

## FINDING-006 — area JSON mob HP/mana/damage dice are mislabeled (field-shifted) — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 via **DB2-007** (master 2.11.2, commit `1857b5f8`).
Root cause was a phantom scalar `ac` token at stat-line index [2] in
`mud/loaders/mob_loader.py` (ROM has no scalar AC there — it's on the next line), which
shifted every dice field by one and dropped the real HP dice. Fixed; all 52 area JSONs
regenerated; full suite 4925/0. The per-file `DB2_C_AUDIT.md` Phase 2 had marked this
stat line ✅ — corrected. Regression: `tests/test_mob_dice_parity.py`.

**Combat-v1 follow-on (not a data bug — normal harness RNG-alignment work):** with the
fix, the drunk #3064 now rolls `2d6+22` on both engines, but the *value* still differs
(C 31, Python 33) because the RNG stream position at `__mload` time isn't yet aligned
between `create_mobile` and `from_prototype` (seeding convention and/or spawn draw
order). The combat scenario's `__seed`-before-`__mload` + matched-stub tasks address
this; the first capture will surface it as the mob's starting-HP diff to triage.

### (historical, root-cause notes below)

**Status:** 🔴 OPEN — **real, systematic Python parity bug.** Surfaced 2026-05-28 while
preparing the combat differential scenario (drunk #3064 spawned at 100 HP in Python
vs 31 in ROM C). **Blocks** `combat_melee_rounds` (the combatant's HP cannot match
across engines until fixed).

**Root cause.** ROM new-format mob stat line (`src/db.c` `load_mobiles`) is
`level hitroll <hp-dice> <mana-dice> <dam-dice> damtype`. The `.are`→JSON conversion
that produced `data/areas/*.json` shifted these by one field:

| JSON field | Holds (wrong) | Should hold |
|------------|---------------|-------------|
| `hit_dice` | the `.are` **mana** dice | the `.are` **HP** dice |
| `mana_dice` | the `.are` **damage** dice | the `.are` **mana** dice |
| `damage_dice` | the **damtype** word (e.g. `"beating"`) | the `.are` **damage** dice |

The real HP dice is dropped entirely. `MobInstance.from_prototype`
(`mud/spawning/templates.py:374`) then rolls `max_hit` from `hit_dice` — i.e. from the
mana dice — so every JSON-loaded mob has the wrong HP, mana, and damage.

**Evidence (drunk #3064, room 3008, seed 777):**
- `area/midgaard.are`: `2 -1 2d6+22 1d1+99 1d6+0 beating` → HP `2d6+22`, mana `1d1+99`, dam `1d6+0`.
- C shim (`src/diffshim`, = ROM loading the `.are`): `max_hp = 31` (a `2d6+22` roll).
- Python `spawn_mob(3064).max_hit = 100` (parsed `1d1+99`, the **mana** dice).
- Hassan #3001 `.are` HP `1d1+999` → ROM 1000 HP; JSON `hit_dice='1d1+99'` → Python 100 HP.

**Scope.** Systematic: **62 of 65** midgaard mobs mismatch on `hit_dice` (the 3 that
"match" do so only because their HP and mana dice are coincidentally equal). Almost
certainly affects **all** `data/areas/*.json`, not just midgaard — i.e. every
JSON-loaded mob game-wide has wrong HP/mana/damage. Latent because the test suite
uses synthetic mobs (`movable_mob_factory` with explicit points), never asserting a
JSON-loaded mob's HP against ROM.

**Fix shape (master, NOT this branch — wide blast radius, needs scoping with the user):**
likely fix the `.are`→JSON converter's field mapping and regenerate every
`data/areas/*.json`, then add a regression that checks a JSON-loaded mob's HP/mana/
damage dice against the `.are`. Route via `rom-gap-closer` once scoped; file the
data-conversion bug in the appropriate tracker. Until fixed, `combat_melee_rounds`
stays uncaptured / out of `KNOWN_DIVERGENCES`.

---

## FINDING-005 — input-source asymmetry (C reads `.are`, Python reads JSON) — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 — investigated, found **structurally benign**,
and locked with a guard test. This was the last harness-soundness follow-up before
`diff-harness` can merge.

The two engines load world data from different sources: the C shim reads the
repaired `midgaard` `.are` overlay (`src/diff_shim/area/`), the Python replay reads
`data/areas/*.json`. The concern (carried from FINDING-001's "separate latent
issue") was that for midgaard scenarios the two might load **different** data and
manufacture false divergences.

**Probe result (2026-05-28):** the JSON and the repaired `.are` cover an
**identical** room/mobile/object vnum set (143 / 65 / 160 each; `only in .are=[]`,
`only in JSON=[]`). The JSON was generated from a correctly-parsed (or pre-repaired)
source — it does **not** drop the entities the malformed stock `area/midgaard.are`
would (the `#`→`#ROOMS` / `~ROOMS`→`~` corruption at the OBJECTS→ROOMS boundary
only ever affected the C-side raw parse, which the overlay repairs). So the
soundness coverage is already complete:
- structural drift (a vnum in one source but not the other) → none today;
- field drift on an entity a scenario exercises → caught by the per-step snapshot diff;
- field drift on a non-exercised entity → invisible but irrelevant (not exercised).

**Fix:** added `tests/test_diff_harness_data_parity.py`, which reconstructs the
repaired `.are` in-Python (byte-identical to the `Makefile.diffshim` `area-overlay`
awk, verified — so it does not depend on the gitignored build artifact) and asserts
its room/mob/object vnum sets equal the JSON the Python loader reads. Any future edit
to either source that desyncs the two engines' world data now fails this guard.

**Not done (deliberately):** repairing stock `area/midgaard.are` + regenerating
`midgaard.json` (Option B). The probe proves it is unnecessary for soundness, and
regenerating the JSON has a wide blast radius across tests asserting current
JSON-loaded state. The overlay + guard is the minimal sound close.

**⚠️ Update (FINDING-006):** this guard checks vnum-set *coverage* only, not field
*values*. FINDING-006 (below) found the JSON's mob HP/mana/damage dice are
field-shifted vs the `.are` — so the two sources are NOT value-equivalent even though
their vnum sets match. The guard should be extended to compare mob dice as part of
FINDING-006's fix.

---

## FINDING-004 — room object list shows obj name, not ROM ground `description` — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 via **LOOK-004** (master 2.10.5, commit `2e5ebf3f`).
The `_describe_room` object loop now emits `obj.description` (ROM
`format_obj_to_char` fShort=FALSE) and skips description-less objects. Merged into
this branch; the differential `movement_get_drop` diff is clean. (Aura/stat
prefixes remain a separate latent gap, noted in the audit.) Original analysis below.

**Status (historical):** Open — **real parity bug** (object analog of FINDING-001/LOOK-001).
Surfaced once the harness output capture was made fair (see "Harness soundness
fixes" below). On `look`/auto-look, ROM lists each object lying in a room by its
**`description`** (the long ground line), e.g. `"A pit for sacrifices is in front
of the altar."` Python (`mud/world/look.py:171-173`) lists `obj.short_descr or
obj.name`, e.g. `"the donation pit"`.
- **ROM C:** `src/act_info.c` `do_look` room display → `show_list_to_char` →
  `format_obj_to_char(obj, ch, FALSE)` emits `obj->description` for ground items.
- **Python:** `mud/world/look.py:172-173` (`_describe_room` object loop).
- **Fix (master gap-closer, e.g. `LOOK-003`/`OBJ-DESC-001`):** show the object's
  `description` for items on the ground; fall back to short_descr only when
  `description` is empty. Mirror the LOOK-001 long_descr approach.
- Gated under `KNOWN_DIVERGENCES["movement_get_drop"]` until fixed on master.

---

## FINDING-003 — movement emits a non-ROM "You walk <dir> to <room>." line — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 via **MOVE-003** (master 2.10.4, commit `ab8f9bd9`).
`move_character` now returns the destination room view (ROM `act_move.c:204`
`do_look "auto"`) instead of the "You walk" line; ~25 assertions across 14 files
were updated to the ROM-faithful output. Merged into this branch; the differential
`movement_get_drop` diff is clean. Original analysis below.

**Status (historical):** Open — **real parity bug.** Surfaced once the harness output capture
was made fair. On `north`/`south`, ROM shows only the destination room
(`do_look auto`); the mover gets **no** "you walk" line. Python
(`mud/world/movement.py:455,470`) returns `"You walk {dir} to {room}."`, which the
live server (`mud/net/connection.py:1981`) sends to the player **before** draining
the auto-look messages — so a Python player sees an extra line AND in the wrong
order (walk-line → room; ROM: room only).
- **ROM C:** `src/act_move.c:204` — `do_function(ch, &do_look, "auto");` is the
  only output to the mover; there is no walk-line anywhere in `move_char`.
- **Python:** `mud/world/movement.py:455` and `:470` (`move_character` return).
- **Fix (master gap-closer, e.g. `MOVE-001`):** drop the `"You walk ..."` return
  string; keep the `_auto_look(char)` call. Note the **ordering** is part of the
  bug — the same fix resolves both (remove the pre-room line, leaving room-only).
  Audit fallout in any test asserting the `"You walk ..."` return.
- Gated under `KNOWN_DIVERGENCES["movement_get_drop"]` until fixed on master.

---

## Harness soundness fixes — 2026-05-28 (this commit)

Three start-state / capture asymmetries that made the harness's diffs untrustworthy
were reconciled (harness-only changes — no ROM `src/` edits, no production `mud/`
edits). These are NOT parity bugs; they were unfairness in the comparison itself:

1. **Test-character HMV (FINDING-002, resolved below).** Python now seeds the
   harness char with ROM `new_char()` defaults (recycle.c:299-304: hp/max=20,
   mana/max=100, move/max=100) so it matches the C shim's `make_test_char`.
   `tests/test_differential_smoke.py`.
2. **Scenario `level` not passed to C.** `capture.py:_drive` boot line now includes
   `level={char_level}` (the C shim already parsed it). Previously C always booted
   at level 1 while Python set the scenario level — a hidden second divergence the
   first-divergence comparator masked behind the hp diff.
3. **Snapshot people-key field.** `pysnap._room_snap` now keys room occupants the
   way the C shim's `char_key` does — first word of ROM's `ch->name`, which for a
   mob is the keyword list (`MobIndex.player_name`, e.g. `"healer"`), not the
   display `short_descr` (`"the healer"`). PCs key on their own name.
4. **Output capture channel.** The replay now captures the full player-visible
   output — the command return value followed by drained `char.messages`
   (send_to_char delivery), mirroring the live server loop
   (`mud/net/connection.py:1979-2000`) — instead of the return value alone. This
   is what surfaced FINDING-003 and FINDING-004 above.

The golden was recaptured (only `char.level` 1→5 changed; output arrays
unchanged, confirming the C side was untouched).

---

## FINDING-002 — test-character hp/level differ between C shim and Python replay — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 — harness-soundness (not a parity bug). Two
parts: (a) Python's `create_test_character` (a shared test stub, not ROM's
new-player path) left hp/mana/move at the dataclass default 0 while the C shim's
`make_test_char` copied ROM `new_char()` defaults (20/100/100); (b) `capture.py`
never passed the scenario `level=` to the C shim, so C booted at level 1 vs
Python's level 5. Both reconciled as harness start-state fixes (see "Harness
soundness fixes" above): the replay seeds the recycle.c HMV defaults and the boot
line now carries `level=`. Golden recaptured. The remaining `movement_get_drop`
divergences are the real parity bugs FINDING-003 + FINDING-004.

---

## FINDING-001 — `look` renders room NPC by name, not ROM long_descr — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 via **LOOK-001** (master 2.10.1) + **LOOK-002**
(2.10.2). It was a real, broad parity bug after all (not the data asymmetry):
`MobInstance` didn't carry `long_descr`/`description` from its prototype (ROM
`create_mobile`) and `mud/world/look.py` used the PERS path instead of
`show_char_to_char_0`'s long_descr branch. Fixed on master; the differential
room/output rendering now matches the C reference exactly. The scenario's
remaining xfail is FINDING-002 (character hp), a separate harness-soundness item.
Historical investigation notes retained below.

### (historical) root-cause investigation

**Status:** ROOT CAUSE CONFIRMED (2026-05-28) — real, broad parity bug; fix
pending (xfailed in `movement_get_drop`). It is **not** the malformed
`midgaard.are`: Python loads area data from JSON (`initialize_world(use_json=True)`),
and the JSON Hassan *prototype* has the correct
`long_descr = "Hassan is here, waiting to dispense some justice.\n"`. The earlier
"diagnostic nondeterminism" was transient (the area overlay was still being
written by the build subagent); it is now stable: 986 mobs, exactly 1
(vnum 2006, unrelated) without a prototype long_descr.

**Confirmed root cause (two parts):**
1. **`mud/world/look.py:151-156`** renders each room occupant via
   `describe_character()` — which returns ROM `PERS` (short_descr/name + affect
   auras), e.g. `"Hassan"`. ROM's `show_char_to_char_0` (`src/act_info.c`)
   instead prints an NPC's **`long_descr`** when `IS_NPC(victim)`, its long_descr
   is non-empty, and `victim->position == victim->default_pos`; otherwise it
   falls back to a `PERS`+position line. So Python uses the wrong renderer for the
   room occupant list — **every room `look` shows NPC names instead of ROM long
   descriptions.**
2. **`mud/spawning/templates.py` `MobInstance`** has no `long_descr` field and
   `from_prototype` never copies it, so even once look.py is fixed the instance
   would read `None`. ROM `create_mobile` (`src/db.c:2040`) does
   `mob->long_descr = str_dup(pMobIndex->long_descr)`.

**Fix shape (a real parity fix — belongs on `master`, not just this branch):**
- Add `long_descr` (and likely `description`) to `MobInstance`; copy from the
  prototype in `from_prototype` (mirror `create_mobile`).
- In `look.py` room-occupant rendering, implement `show_char_to_char_0`: for an
  NPC in its `default_pos` with a non-empty `long_descr`, emit the long_descr
  (with affect prefixes); else fall back to the existing PERS+position path.
- **Wide blast radius:** changes room-look output for ALL NPCs game-wide. Expect
  fallout in any test asserting the current name-based room rendering — triage
  each (a test asserting non-ROM behavior is a test bug per AGENTS.md). Do this
  as a `/rom-gap-closer` with a failing test first.
- When fixed, the differential `movement_get_drop` diff goes clean and the
  `KNOWN_DIVERGENCES` entry is removed.

**Separate latent issue (harness soundness, not FINDING-001):** the C side reads
`.are` files (a repaired midgaard overlay) while Python reads `data/areas/*.json`.
For midgaard-based scenarios the two engines load from different sources. **This is
now resolved — see FINDING-005:** the two sources were proven to cover an identical
vnum set, and `tests/test_diff_harness_data_parity.py` guards the equivalence.

### (historical) original triage notes

**Symptom:** In room 3001 (Temple of Mota), `look`:
- ROM C: `Hassan is here, waiting to dispense some justice.` (mob `long_descr`)
- Python: `Hassan` (mob name)

Every other room-description line matches byte-for-byte after normalization;
this is the only divergence in the movement_get_drop scenario.

**Why the root cause is ambiguous (two confounded causes):**

1. **Unequal inputs (harness fairness).** `area/midgaard.are` is malformed vs
   stock ROM 2.4 (bare `#` instead of `#ROOMS` at the OBJECTS→ROOMS boundary;
   the `ROOMS` keyword migrated onto the previous record's `~` terminator as
   `~ROOMS`). The C shim reads a **repaired** midgaard via a generated overlay
   (`src/diff_shim/area/`), while the Python replay reads the **original**
   `area/midgaard.are`. So for midgaard rooms the two engines may not be reading
   identical data, which can manufacture false-positive divergences. This must
   be reconciled before midgaard divergences can be trusted as real: either
   repair `area/midgaard.are` in the tracked data (so both engines read the
   well-formed file) or point the Python replay at the same repaired overlay.

2. **Possible prototype-vs-instance `long_descr` gap (unconfirmed).** Direct
   inspection showed the spawned Hassan *instance* in `room.people` had
   `long_descr = None`, yet a sweep of `mob_registry` *prototypes* returned
   inconsistent counts across identical runs (one run: 1 mob without long_descr;
   the next: 0). **That nondeterminism is itself unexplained and must be pinned
   first** — it may indicate registry state leakage or that instances don't
   inherit `long_descr` from their prototype. Until it's understood, do not
   conclude this is purely a data problem.

**Next triage steps (separate session):**
1. Pin the `mob_registry` long_descr count nondeterminism (run the same probe
   repeatedly; identify what state differs).
2. Reconcile inputs: parse the *repaired* midgaard with the Python loader and
   check whether Hassan's `long_descr` populates. If yes → the cause is the
   malformed `area/midgaard.are`; repair it (matching stock ROM) so both engines
   read the same data, then re-run the harness.
3. If `long_descr` is still `None` from a well-formed file → real Python
   loader/instance bug; fix it (ROM is source of truth) and file the gap.
4. When the diff goes clean, remove the `movement_get_drop` entry from
   `KNOWN_DIVERGENCES`.

**Meta:** This is the harness working as intended — it found a real
discrepancy (and a data-integrity question about `midgaard.are`) on its first
run. The value is in surfacing it; the fix is deliberately deferred so the
harness can land green-with-findings.
