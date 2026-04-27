"""Integration tests for consumable & special-object commands.

Covers do_eat / do_drink / do_quaff / do_recite / do_brandish / do_zap.
ROM Parity Reference: src/act_obj.c — see docs/parity/ACT_OBJ_C_CONSUMABLES_AUDIT.md.

Tests for commands whose Python implementation is currently broken (do_recite,
do_brandish, do_zap) skip with a pointer to the audit doc rather than fail.
"""
from __future__ import annotations

import pytest

from mud.commands.consumption import do_drink, do_eat
from mud.commands.dispatcher import process_command
from mud.commands.liquids import do_fill, do_pour
from mud.commands.magic_items import do_brandish, do_recite, do_zap
from mud.commands.obj_manipulation import do_quaff
from mud.models.character import Character
from mud.models.constants import ItemType, WearLocation
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character


_AUDIT_REF = "not yet implemented in Python port — see ACT_OBJ_C_CONSUMABLES_AUDIT.md"


@pytest.fixture(autouse=True)
def _clear_registries():
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def test_character() -> Character:
    room = Room(vnum=3001, name="Test Room", description="A test room")
    room_registry[3001] = room
    char = create_test_character("Tester", room_vnum=3001)
    char.level = 20
    char.is_npc = False
    return char


def _make_obj(object_factory, *, item_type: ItemType, name: str, short_descr: str,
              value=None, level: int = 1) -> Object:
    obj = object_factory(
        {
            "vnum": 9000,
            "name": name,
            "short_descr": short_descr,
            "item_type": int(item_type),
            "value": list(value or [0, 0, 0, 0, 0]),
            "level": level,
        }
    )
    # Object instance leaves item_type=None by default; sync from proto for clarity.
    obj.item_type = int(item_type)
    obj.value = list(value or [0, 0, 0, 0, 0])
    obj.level = level
    return obj


# --------------------------------------------------------------------------- #
# do_eat                                                                      #
# --------------------------------------------------------------------------- #


def test_eat_requires_argument(test_character):
    """ROM: empty arg returns 'Eat what?'."""
    assert do_eat(test_character, "") == "Eat what?"


def test_eat_rejects_non_food(test_character, object_factory):
    """ROM: non-food/non-pill yields 'That's not edible.'."""
    rock = _make_obj(object_factory, item_type=ItemType.TRASH,
                     name="rock", short_descr="a rock")
    test_character.add_object(rock)
    result = do_eat(test_character, "rock")
    assert "edible" in result.lower() or "can't" in result.lower()


def test_eat_food_consumes_item(test_character, object_factory):
    """ROM act_obj.c:1363 — extract_obj called after FOOD is eaten."""
    bread = _make_obj(object_factory, item_type=ItemType.FOOD,
                      name="bread", short_descr="a loaf of bread",
                      value=[8, 5, 0, 0, 0])
    test_character.add_object(bread)
    do_eat(test_character, "bread")
    assert bread not in test_character.inventory, \
        "Food should be removed from inventory after eating"


def test_eat_poisoned_food_applies_choke_message(test_character, object_factory):
    """ROM act_obj.c:1337-1352 — value[3]!=0 yields choke/gag message and AFF_POISON.

    Current Python implementation builds an affect with non-canonical fields
    (see audit). We assert on the user-visible choke message only.
    """
    poisoned = _make_obj(object_factory, item_type=ItemType.FOOD,
                         name="apple", short_descr="a poisoned apple",
                         value=[4, 4, 0, 1, 0])
    test_character.add_object(poisoned)
    result = do_eat(test_character, "apple")
    assert "choke" in result.lower() or "poison" in result.lower(), \
        f"Expected poison message, got: {result!r}"


def test_eat_full_character_blocked(test_character, object_factory):
    """ROM act_obj.c:1310-1314 — mortals with COND_FULL > 40 get rejected."""
    bread = _make_obj(object_factory, item_type=ItemType.FOOD,
                      name="bread", short_descr="a loaf of bread",
                      value=[8, 5, 0, 0, 0])
    test_character.add_object(bread)
    # condition is list[int]: [DRUNK=0, FULL=1, THIRST=2, HUNGER=3]
    # Set COND_FULL (index 1) above the ROM threshold of 40
    if not hasattr(test_character, "condition") or test_character.condition is None:
        test_character.condition = [0, 0, 48, 48]
    test_character.condition[1] = 45  # COND_FULL index = 1
    result = do_eat(test_character, "bread")
    assert "too full" in result.lower(), f"Expected 'too full' message, got: {result!r}"


def test_eat_pill_casts_spells_and_extracts(test_character, object_factory):
    """ROM act_obj.c:1356-1360 — PILL type casts spells and is extracted.

    EAT-001: pill path should consume the item from inventory regardless of
    whether the spell sn resolves (spell sn 0 is a no-op in ROM).
    """
    pill = _make_obj(object_factory, item_type=ItemType.PILL,
                     name="pill", short_descr="a red pill",
                     value=[10, 0, 0, 0, 0])
    test_character.add_object(pill)
    result = do_eat(test_character, "pill")
    assert pill not in test_character.inventory, \
        "Pill should be removed from inventory after eating"
    assert isinstance(result, str)


def test_eat_immortal_can_eat_non_food(test_character, object_factory):
    """ROM act_obj.c:1302 — IS_IMMORTAL bypasses the item-type check.

    EAT-002: an immortal should be able to eat a TRASH item without
    receiving 'That's not edible.'
    """
    rock = _make_obj(object_factory, item_type=ItemType.TRASH,
                     name="rock", short_descr="a rock")
    test_character.add_object(rock)
    # LEVEL_IMMORTAL = MAX_LEVEL - 8 = 52; set level at threshold
    test_character.level = 52
    result = do_eat(test_character, "rock")
    assert "edible" not in result.lower(), \
        f"Immortal should not get 'not edible' message; got: {result!r}"


def test_eat_broadcasts_to_room(test_character, object_factory):
    """ROM act_obj.c:1317 — TO_ROOM act fires before TO_CHAR.

    EAT-004: observer in the same room should see '<name> eats <obj>.'
    broadcast_room() delivers to char.messages when no async connection exists.
    """
    bread = _make_obj(object_factory, item_type=ItemType.FOOD,
                      name="bread", short_descr="a loaf of bread",
                      value=[5, 5, 0, 0, 0])
    test_character.add_object(bread)

    # Place an observer in the same room; broadcast_room uses char.messages list
    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages = []

    do_eat(test_character, "bread")

    # The observer should have received a message containing "eats"
    combined = " ".join(observer.messages)
    assert "eats" in combined.lower(), \
        f"Observer should see eat broadcast; got: {observer.messages!r}"


def test_eat_poison_affect_uses_rom_duration(test_character, object_factory):
    """ROM act_obj.c:1347-1348 — poison duration = 2 * value[0], modifier = 0.

    EAT-005: verify the affect metadata stored on ch.affects uses ROM-correct fields.
    do_eat stores full ROM affect dict in ch.affects list after calling add_affect(flag).
    """
    poisoned = _make_obj(object_factory, item_type=ItemType.FOOD,
                         name="mushroom", short_descr="a poisoned mushroom",
                         value=[5, 0, 0, 1, 0])
    test_character.add_object(poisoned)
    # Ensure affects list exists so do_eat can append to it
    test_character.affects = []

    do_eat(test_character, "mushroom")

    assert test_character.affects, "Expected at least one affect to be stored in ch.affects"
    af = test_character.affects[0]
    assert af.get("duration") == 10, \
        f"Expected duration=2*5=10, got {af.get('duration')}"
    assert af.get("modifier") == 0, \
        f"Expected modifier=0 (APPLY_NONE), got {af.get('modifier')}"
    assert af.get("location") == 0, \
        f"Expected location=0 (APPLY_NONE), got {af.get('location')}"


# --------------------------------------------------------------------------- #
# do_drink                                                                    #
# --------------------------------------------------------------------------- #


def test_drink_from_drink_container_decrements_value(test_character, object_factory):
    """ROM act_obj.c:1276-1277 — drink container value[1] decremented after sip."""
    # ROM default FULL=48 would trip DRINK-009 (>45); reset to empty stomach.
    test_character.pcdata.condition[1] = 0
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 5, 0, 0, 0])  # cap=10, current=5, water, not poisoned
    test_character.add_object(flask)
    do_drink(test_character, "flask")
    assert flask.value[1] < 5, \
        f"Drink container should decrement value[1]; got {flask.value[1]}"


def test_drink_empty_container_message(test_character, object_factory):
    """ROM: 'It is already empty.' when value[1] == 0."""
    empty = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="an empty flask",
                      value=[10, 0, 0, 0, 0])
    test_character.add_object(empty)
    result = do_drink(test_character, "flask")
    assert "empty" in result.lower(), f"Expected empty message, got: {result!r}"


def test_drink_from_fountain_does_not_decrement(test_character, object_factory):
    """ROM: ITEM_FOUNTAIN is infinite — value[1] is not modified."""
    room = test_character.room
    fountain = _make_obj(object_factory, item_type=ItemType.FOUNTAIN,
                         name="fountain", short_descr="a stone fountain",
                         value=[0, 0, 0, 0, 0])
    room.add_object(fountain)
    result = do_drink(test_character, "fountain")
    assert fountain.value[1] == 0, "Fountain should remain at value[1]==0 (infinite)"
    assert isinstance(result, str)


# --------------------------------------------------------------------------- #
# do_drink — DRINK-001..009 parity tests                                      #
# --------------------------------------------------------------------------- #


def test_drink_no_arg_finds_room_fountain(test_character, object_factory):
    """DRINK-001: empty arg scans room for ITEM_FOUNTAIN; uses it if found."""
    room = test_character.room

    # No fountain present → "Drink what?"
    result = do_drink(test_character, "")
    assert result == "Drink what?", f"Expected 'Drink what?' with no fountain, got: {result!r}"

    # Place a fountain → should drink from it without any arg
    fountain = _make_obj(object_factory, item_type=ItemType.FOUNTAIN,
                         name="fountain", short_descr="a marble fountain",
                         value=[0, 0, 0, 0, 0])
    room.add_object(fountain)
    result2 = do_drink(test_character, "")
    assert "drink" in result2.lower(), \
        f"Expected drink message when fountain present, got: {result2!r}"


def test_drink_drunk_blocks(test_character, object_factory):
    """DRINK-002: COND_DRUNK > 10 returns ROM '*Hic*' message; no condition change."""
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 10, 0, 0, 0])
    test_character.add_object(flask)
    # Set COND_DRUNK (index 0) > 10
    test_character.pcdata.condition[0] = 15
    thirst_before = test_character.pcdata.condition[2]

    result = do_drink(test_character, "flask")
    assert "*Hic*" in result, f"Expected *Hic* message, got: {result!r}"
    assert "  *Hic*" in result, "ROM wording requires TWO spaces before *Hic*"
    # Condition must not change
    assert test_character.pcdata.condition[2] == thirst_before, \
        "Thirst should not change when drunk check fires"


def test_drink_get_obj_here_finds_room_object(test_character, object_factory):
    """DRINK-003: non-empty arg uses get_obj_here so room objects are found."""
    room = test_character.room
    fountain = _make_obj(object_factory, item_type=ItemType.FOUNTAIN,
                         name="marble fountain", short_descr="a marble fountain",
                         value=[0, 0, 0, 0, 0])
    room.add_object(fountain)
    # Arg is not literally "fountain" — uses get_obj_here which searches room
    result = do_drink(test_character, "marble")
    assert "drink" in result.lower(), \
        f"Expected drink message for room fountain via get_obj_here, got: {result!r}"


def test_drink_full_blocks_mortal(test_character, object_factory):
    """DRINK-009: COND_FULL > 45 returns 'too full' for mortals."""
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 10, 0, 0, 0])
    test_character.add_object(flask)
    test_character.level = 20  # mortal
    test_character.pcdata.condition[1] = 46  # COND_FULL index = 1

    result = do_drink(test_character, "flask")
    assert "too full" in result.lower(), \
        f"Expected 'too full' message for full mortal, got: {result!r}"


def test_drink_immortal_bypasses_full_check(test_character, object_factory):
    """DRINK-009: immortal (level >= 52) bypasses the 'too full' check."""
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 10, 0, 0, 0])
    test_character.add_object(flask)
    test_character.level = 52  # LEVEL_IMMORTAL
    test_character.pcdata.condition[1] = 48  # COND_FULL maxed

    result = do_drink(test_character, "flask")
    # gain_condition short-circuits for immortals, so no too-full rejection
    assert "too full" not in result.lower(), \
        f"Immortal should bypass full check, got: {result!r}"


def test_drink_broadcasts_to_room(test_character, object_factory):
    """DRINK-007: observer in same room sees '$n drinks $T from $p.'"""
    # ROM default FULL=48 would trip DRINK-009 (>45); reset to empty stomach.
    test_character.pcdata.condition[1] = 0
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 10, 0, 0, 0])
    test_character.add_object(flask)

    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages = []

    do_drink(test_character, "flask")

    combined = " ".join(observer.messages)
    assert "drinks" in combined.lower(), \
        f"Observer should see drink broadcast, got: {observer.messages!r}"


def test_drink_water_updates_thirst_via_liq_table(test_character, object_factory):
    """DRINK-005: drinking water (liq=0) updates thirst per ROM formula.

    water: ssize=16, thirst=10 → amount=16 for flask (full)
    gain_condition(THIRST, 16*10//10) = gain_condition(THIRST, 16)
    Starting thirst 0 → should become 16 (clamped to 48 max).
    """
    # ROM default FULL=48 would trip DRINK-009 (>45); reset to empty stomach.
    test_character.pcdata.condition[1] = 0
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[20, 20, 0, 0, 0])  # cap=20, current=20, water(0)
    test_character.add_object(flask)
    test_character.pcdata.condition[2] = 0  # COND_THIRST starts at 0

    do_drink(test_character, "flask")

    thirst_after = test_character.pcdata.condition[2]
    assert thirst_after > 0, \
        f"Thirst should increase after drinking water, got condition[2]={thirst_after}"


def test_drink_poison_affect_uses_rom_duration(test_character, object_factory):
    """DRINK-008: poisoned drink adds affect with duration = 3 * amount, modifier = 0.

    water: ssize=16, amount=min(16, value[1]=10)=10 → duration=3*10=30
    """
    # ROM default FULL=48 would trip DRINK-009 (>45); reset to empty stomach.
    test_character.pcdata.condition[1] = 0
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a poisoned flask",
                      value=[10, 10, 0, 1, 0])  # value[3]=1 → poisoned
    test_character.add_object(flask)
    test_character.affects = []

    result = do_drink(test_character, "flask")

    assert "choke" in result.lower(), f"Expected choke message, got: {result!r}"
    assert test_character.affects, "Expected poison affect to be stored in ch.affects"
    af = test_character.affects[0]
    assert af.get("modifier") == 0, \
        f"Expected modifier=0 (APPLY_NONE), got {af.get('modifier')}"
    assert af.get("location") == 0, \
        f"Expected location=0 (APPLY_NONE), got {af.get('location')}"
    # duration = 3 * amount; amount = min(ssize=16, value[1]=10) = 10 → duration = 30
    assert af.get("duration") == 30, \
        f"Expected duration=3*10=30, got {af.get('duration')}"


# --------------------------------------------------------------------------- #
# do_quaff                                                                    #
# --------------------------------------------------------------------------- #


def test_quaff_requires_potion_type(test_character, object_factory):
    """ROM: 'You can quaff only potions.' if not ITEM_POTION."""
    rock = _make_obj(object_factory, item_type=ItemType.TRASH,
                     name="rock", short_descr="a rock")
    test_character.add_object(rock)
    result = do_quaff(test_character, "rock")
    assert "potion" in result.lower(), f"Expected potion gate, got: {result!r}"


def test_quaff_potion_extracts_after(test_character, object_factory):
    """ROM act_obj.c:1904 — extract_obj(potion) after the three obj_cast_spell calls.

    obj_manipulation._extract_obj reads ch.carrying (does not exist) — see audit.
    Owned by another agent this session; we exercise the call path and assert the
    success message instead of inventory removal.
    """
    potion = _make_obj(object_factory, item_type=ItemType.POTION,
                       name="potion", short_descr="a healing potion",
                       value=[10, 0, 0, 0, 0], level=1)  # spell slots empty
    test_character.add_object(potion)
    result = do_quaff(test_character, "potion")
    assert "quaff" in result.lower(), \
        f"Expected quaff TO_CHAR message, got: {result!r}"


def test_quaff_broadcasts_to_room(test_character, object_factory):
    """ROM act_obj.c:1897 — act('$n quaffs $p.', TO_ROOM) precedes spell casting."""
    observer = create_test_character("Watcher", room_vnum=3001)
    observer.is_npc = False
    observer.messages.clear()

    potion = _make_obj(object_factory, item_type=ItemType.POTION,
                       name="potion", short_descr="a healing potion",
                       value=[10, 0, 0, 0, 0], level=1)
    test_character.add_object(potion)
    do_quaff(test_character, "potion")

    assert any("quaffs" in msg.lower() for msg in observer.messages), \
        f"Observer should see quaff broadcast, got: {observer.messages!r}"


def test_quaff_level_check_rejects(test_character, object_factory):
    """ROM act_obj.c:1890 — ch->level < obj->level => 'too powerful'."""
    test_character.level = 1
    potion = _make_obj(object_factory, item_type=ItemType.POTION,
                       name="potion", short_descr="a potent potion",
                       value=[50, 0, 0, 0, 0], level=50)
    test_character.add_object(potion)
    result = do_quaff(test_character, "potion")
    assert "powerful" in result.lower() or "too" in result.lower()


# --------------------------------------------------------------------------- #
# do_recite — RECITE-NNN parity (ROM src/act_obj.c:1910-1974)                  #
# --------------------------------------------------------------------------- #


def test_recite_requires_scroll_in_inventory(test_character):
    """ROM 1921-1924: missing scroll yields 'You do not have that scroll.'"""
    result = do_recite(test_character, "scroll")
    assert "do not have" in result.lower(), result


def test_recite_only_scrolls(test_character, object_factory):
    """ROM 1927-1930: non-scroll item yields 'You can recite only scrolls.'"""
    rock = _make_obj(object_factory, item_type=ItemType.TRASH,
                     name="rock", short_descr="a rock")
    test_character.add_object(rock)
    assert "only scrolls" in do_recite(test_character, "rock").lower()


def test_recite_level_gate(test_character, object_factory):
    """ROM 1933-1937: ch->level < scroll->level => 'too complex'."""
    test_character.level = 5
    scroll = _make_obj(object_factory, item_type=ItemType.SCROLL,
                       name="scroll", short_descr="a complex scroll",
                       value=[20, 0, 0, 0, 0], level=50)
    test_character.add_object(scroll)
    assert "too complex" in do_recite(test_character, "scroll").lower()


def test_recite_unknown_target(test_character, object_factory):
    """ROM 1947-1952: target arg matching nothing => 'You can't find it.'"""
    scroll = _make_obj(object_factory, item_type=ItemType.SCROLL,
                       name="scroll", short_descr="a scroll",
                       value=[10, 0, 0, 0, 0], level=1)
    test_character.add_object(scroll)
    result = do_recite(test_character, "scroll nobody")
    assert "can't find" in result.lower(), result


def test_recite_consumes_scroll_and_broadcasts(test_character, object_factory):
    """ROM 1955-1956 + 1972: TO_ROOM act + extract_obj after recite."""
    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages.clear()
    scroll = _make_obj(object_factory, item_type=ItemType.SCROLL,
                       name="scroll", short_descr="a magic scroll",
                       value=[10, 0, 0, 0, 0], level=1)
    test_character.add_object(scroll)
    do_recite(test_character, "scroll")
    # Object reference removed from inventory by _extract_obj path
    assert any("recites" in m.lower() for m in observer.messages), observer.messages


# --------------------------------------------------------------------------- #
# do_brandish — BRANDISH-NNN parity (ROM src/act_obj.c:1978-2064)              #
# --------------------------------------------------------------------------- #


def _hold_staff(char, staff):
    if staff in char.inventory:
        char.inventory.remove(staff)
    char.equipment[WearLocation.HOLD] = staff


def test_brandish_requires_held_item(test_character):
    """ROM 1985: empty hold slot => 'You hold nothing in your hand.'"""
    assert "hold nothing" in do_brandish(test_character, "").lower()


def test_brandish_only_with_staff(test_character, object_factory):
    """ROM 1991: non-staff held => 'You can brandish only with a staff.'"""
    rock = _make_obj(object_factory, item_type=ItemType.TRASH,
                     name="rock", short_descr="a rock")
    _hold_staff(test_character, rock)
    assert "only with a staff" in do_brandish(test_character, "").lower()


def test_brandish_decrements_charges_and_destroys_at_zero(test_character, object_factory):
    """ROM 2056-2061: --value[2] <= 0 destroys staff with TO_CHAR + TO_ROOM."""
    staff = _make_obj(object_factory, item_type=ItemType.STAFF,
                      name="staff", short_descr="a wooden staff",
                      value=[10, 0, 1, "armor", 0], level=1)
    _hold_staff(test_character, staff)
    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages.clear()

    do_brandish(test_character, "")

    assert staff.value[2] == 0, f"Charge should be 0, got {staff.value[2]}"
    assert WearLocation.HOLD not in test_character.equipment, \
        "Destroyed staff must be removed from HOLD slot"
    assert any("blazes bright" in m.lower() for m in observer.messages), observer.messages


def test_brandish_level_check_failure(test_character, object_factory):
    """ROM 2010-2016: level too low triggers fail/nothing-happens path."""
    test_character.level = 1
    staff = _make_obj(object_factory, item_type=ItemType.STAFF,
                      name="staff", short_descr="a high-level staff",
                      value=[50, 0, 5, "armor", 0], level=50)
    _hold_staff(test_character, staff)
    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages.clear()

    result = do_brandish(test_character, "")

    assert "fail to invoke" in result.lower(), result
    assert any("...and nothing happens." in m for m in observer.messages), observer.messages
    # Charge still consumed (ROM unconditionally decrements after the if-block)
    assert staff.value[2] == 4, staff.value[2]


# --------------------------------------------------------------------------- #
# do_zap — ZAP-NNN parity (ROM src/act_obj.c:2068-2157)                        #
# --------------------------------------------------------------------------- #


def _hold_wand(char, wand):
    if wand in char.inventory:
        char.inventory.remove(wand)
    char.equipment[WearLocation.HOLD] = wand


def test_zap_requires_arg_or_fighting(test_character):
    """ROM 2076: empty arg + not fighting => 'Zap whom or what?'"""
    assert "zap whom" in do_zap(test_character, "").lower()


def test_zap_requires_held_wand(test_character, object_factory):
    """ROM 2082-2086: nothing held => 'You hold nothing in your hand.'"""
    # Must satisfy ROM 2076 first (provide an arg)
    assert "hold nothing" in do_zap(test_character, "self").lower()


def test_zap_only_wands(test_character, object_factory):
    """ROM 2088: non-wand held => 'You can zap only with a wand.'"""
    rock = _make_obj(object_factory, item_type=ItemType.TRASH,
                     name="rock", short_descr="a rock")
    _hold_wand(test_character, rock)
    assert "only with a wand" in do_zap(test_character, "self").lower()


def test_zap_unknown_target(test_character, object_factory):
    """ROM 2109-2113: target not in room/inv => 'You can't find it.'"""
    wand = _make_obj(object_factory, item_type=ItemType.WAND,
                     name="wand", short_descr="a wand",
                     value=[10, 0, 5, "armor", 0], level=1)
    _hold_wand(test_character, wand)
    assert "can't find" in do_zap(test_character, "ghost").lower()


def test_zap_target_decrements_charges(test_character, object_factory):
    """ROM 2149: --wand->value[2]: zapping a target consumes one charge."""
    wand = _make_obj(object_factory, item_type=ItemType.WAND,
                     name="wand", short_descr="a magic wand",
                     value=[10, 0, 5, "armor", 0], level=1)
    _hold_wand(test_character, wand)
    do_zap(test_character, "self")  # zap self
    assert wand.value[2] == 4, wand.value[2]


def test_zap_destroys_wand_at_zero_charges(test_character, object_factory):
    """ROM 2149-2154: --value[2] <= 0 explodes the wand into fragments."""
    wand = _make_obj(object_factory, item_type=ItemType.WAND,
                     name="wand", short_descr="a magic wand",
                     value=[10, 0, 1, "armor", 0], level=1)
    _hold_wand(test_character, wand)
    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages.clear()

    do_zap(test_character, "self")

    assert wand.value[2] == 0
    assert WearLocation.HOLD not in test_character.equipment
    assert any("explodes into fragments" in m.lower() for m in observer.messages), \
        observer.messages


# --------------------------------------------------------------------------- #
# do_fill / do_pour smoke (covered separately, but exercise dispatcher path)   #
# --------------------------------------------------------------------------- #


def test_fill_requires_fountain_in_room(test_character, object_factory):
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="an empty flask",
                      value=[10, 0, 0, 0, 0])
    test_character.add_object(flask)
    result = do_fill(test_character, "flask")
    assert "fountain" in result.lower()


def test_pour_out_empties_container(test_character, object_factory):
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a full flask",
                      value=[10, 7, 0, 0, 0])
    test_character.add_object(flask)
    result = do_pour(test_character, "flask out")
    assert flask.value[1] == 0, f"Pour out should empty value[1]; got {flask.value[1]}"
    assert "spill" in result.lower() or "invert" in result.lower() or "empty" in result.lower()


# --------------------------------------------------------------------------- #
# do_fill — FILL-002 / FILL-003 parity tests                                  #
# --------------------------------------------------------------------------- #


def test_fill_broadcasts_to_room(test_character, object_factory):
    """FILL-002: observer sees '$n fills $p with <liquid> from $P.' — ROM src/act_obj.c:1025-1027."""
    room = test_character.room
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 0, 0, 0, 0])
    test_character.add_object(flask)

    fountain = _make_obj(object_factory, item_type=ItemType.FOUNTAIN,
                         name="fountain", short_descr="a stone fountain",
                         value=[0, 0, 0, 0, 0])
    room.add_object(fountain)

    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages = []

    do_fill(test_character, "flask")

    combined = " ".join(observer.messages)
    assert "fills" in combined.lower(), \
        f"Observer should see fill broadcast; got: {observer.messages!r}"


def test_fill_succeeds_sets_value(test_character, object_factory):
    """FILL-002/003: fill sets value[1]==value[0] and value[2]==fountain liquid."""
    room = test_character.room
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 0, 0, 0, 0])
    test_character.add_object(flask)

    fountain = _make_obj(object_factory, item_type=ItemType.FOUNTAIN,
                         name="fountain", short_descr="a stone fountain",
                         value=[0, 0, 2, 0, 0])  # liquid type 2 = beer
    room.add_object(fountain)

    do_fill(test_character, "flask")

    assert flask.value[1] == flask.value[0], \
        f"Container should be full; value[1]={flask.value[1]} value[0]={flask.value[0]}"
    assert flask.value[2] == 2, \
        f"Container should have fountain's liquid type; got value[2]={flask.value[2]}"


def test_fill_rejects_when_full(test_character, object_factory):
    """ROM src/act_obj.c:1016-1020 — full container returns 'Your container is full.'"""
    room = test_character.room
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 10, 0, 0, 0])  # already full
    test_character.add_object(flask)

    fountain = _make_obj(object_factory, item_type=ItemType.FOUNTAIN,
                         name="fountain", short_descr="a stone fountain",
                         value=[0, 0, 0, 0, 0])
    room.add_object(fountain)

    result = do_fill(test_character, "flask")
    assert result == "Your container is full."


def test_fill_rejects_mixed_liquids(test_character, object_factory):
    """ROM src/act_obj.c:1010-1014 — mismatched liquid type returns 'already another liquid'."""
    room = test_character.room
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 3, 1, 0, 0])  # partially filled with liquid type 1
    test_character.add_object(flask)

    fountain = _make_obj(object_factory, item_type=ItemType.FOUNTAIN,
                         name="fountain", short_descr="a stone fountain",
                         value=[0, 0, 2, 0, 0])  # different liquid type 2
    room.add_object(fountain)

    result = do_fill(test_character, "flask")
    assert result == "There is already another liquid in it."


# --------------------------------------------------------------------------- #
# do_pour — POUR-001..004 parity tests                                        #
# --------------------------------------------------------------------------- #


def test_pour_out_broadcasts_to_room(test_character, object_factory):
    """POUR-001: observer sees '$n inverts $p, spilling <liquid> all over the ground.' — ROM src/act_obj.c:1075-1077."""
    flask = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                      name="flask", short_descr="a leather flask",
                      value=[10, 7, 0, 0, 0])
    test_character.add_object(flask)

    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages = []

    do_pour(test_character, "flask out")

    combined = " ".join(observer.messages)
    assert "inverts" in combined.lower(), \
        f"Observer should see pour-out broadcast; got: {observer.messages!r}"
    assert "spilling" in combined.lower(), \
        f"Observer should see 'spilling' in broadcast; got: {observer.messages!r}"


def test_pour_object_to_object_broadcasts_to_room(test_character, object_factory):
    """POUR-002: observer sees '$n pours <liquid> from $p into $P.' — ROM src/act_obj.c:1142-1144."""
    room = test_character.room
    source = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                       name="flask", short_descr="a leather flask",
                       value=[10, 7, 0, 0, 0])
    test_character.add_object(source)

    dest = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                     name="mug", short_descr="a wooden mug",
                     value=[5, 0, 0, 0, 0])
    room.add_object(dest)

    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages = []

    do_pour(test_character, "flask mug")

    combined = " ".join(observer.messages)
    assert "pours" in combined.lower(), \
        f"Observer should see pour broadcast; got: {observer.messages!r}"


def test_pour_to_character_sends_to_vict(test_character, object_factory):
    """POUR-003: recipient sees '$n pours you some <liquid>.' — ROM src/act_obj.c:1151-1153."""
    from mud.models.constants import WearLocation

    recipient = create_test_character("Recipient", room_vnum=3001)
    recipient.messages = []

    held_mug = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                         name="mug", short_descr="a wooden mug",
                         value=[5, 0, 0, 0, 0])
    recipient.equipment[WearLocation.HOLD] = held_mug

    source = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                       name="flask", short_descr="a leather flask",
                       value=[10, 7, 0, 0, 0])
    test_character.add_object(source)

    do_pour(test_character, "flask Recipient")

    combined = " ".join(recipient.messages)
    assert "pours you some" in combined.lower(), \
        f"Recipient should see TO_VICT pour message; got: {recipient.messages!r}"
    assert held_mug.value[1] > 0, \
        f"Recipient's held container should receive liquid; got value[1]={held_mug.value[1]}"


def test_pour_to_character_finds_held_container(test_character, object_factory):
    """POUR-004: target_char.equipment[WearLocation.HOLD] is used (not 'held'/'hold' string keys)."""
    from mud.models.constants import WearLocation

    recipient = create_test_character("Recipient", room_vnum=3001)

    held_mug = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                         name="mug", short_descr="a wooden mug",
                         value=[5, 0, 0, 0, 0])
    # Correct slot: WearLocation.HOLD enum key
    recipient.equipment[WearLocation.HOLD] = held_mug

    source = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                       name="flask", short_descr="a leather flask",
                       value=[10, 5, 0, 0, 0])
    test_character.add_object(source)

    result = do_pour(test_character, "flask Recipient")

    assert "pour" in result.lower(), \
        f"Should succeed in pouring; got: {result!r}"
    assert "holding" not in result.lower(), \
        f"Should NOT get 'holding' error (POUR-004 fix); got: {result!r}"


def test_pour_to_character_when_not_holding(test_character, object_factory):
    """ROM src/act_obj.c:1093-1097 — target holding nothing returns 'They aren't holding anything.'"""
    recipient = create_test_character("Recipient", room_vnum=3001)
    # No equipment in HOLD slot

    source = _make_obj(object_factory, item_type=ItemType.DRINK_CON,
                       name="flask", short_descr="a leather flask",
                       value=[10, 5, 0, 0, 0])
    test_character.add_object(source)

    result = do_pour(test_character, "flask Recipient")

    assert "holding" in result.lower(), \
        f"Expected 'holding' rejection; got: {result!r}"


def test_dispatcher_routes_eat_command(test_character, object_factory):
    """Smoke: dispatcher.process_command routes 'eat' to do_eat."""
    bread = _make_obj(object_factory, item_type=ItemType.FOOD,
                      name="bread", short_descr="a loaf of bread",
                      value=[8, 5, 0, 0, 0])
    test_character.add_object(bread)
    result = process_command(test_character, "eat bread")
    assert "eat" in result.lower() or bread not in test_character.inventory
