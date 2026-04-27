"""Integration tests for PUT-003: Pit timer handling in do_put().

ROM Parity References:
- src/act_obj.c:426-433 (single object put pit timer logic)
- src/act_obj.c:465-472 (put all pit timer logic)

This test suite verifies that QuickMUD handles pit timer assignment correctly
when putting objects in the donation pit, matching ROM 2.4b6 behavior.

ROM C Reference (act_obj.c lines 426-433):
    if (container->pIndexData->vnum == OBJ_VNUM_PIT
        && !CAN_WEAR(container, ITEM_TAKE))
    {
        if (obj->timer)
            SET_BIT(obj->extra_flags, ITEM_HAD_TIMER);
        else
            obj->timer = number_range(100, 200);
    }
"""

from __future__ import annotations

import pytest

from mud.commands.obj_manipulation import do_put
from mud.models.constants import ExtraFlag, ItemType, OBJ_VNUM_PIT, WearFlag
from mud.models.object import ObjIndex, Object
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def _initialize_world():
    """Initialize world once for all tests in this module."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def test_room_3001():
    """Ensure room 3001 exists for testing."""
    from mud.models.room import Room

    if 3001 not in room_registry:
        room = Room(vnum=3001, name="Test Room", description="A test room")
        room_registry[3001] = room
    return room_registry[3001]


@pytest.fixture(autouse=True)
def clean_test_objects(test_room_3001):
    """Remove test-created objects from registry and room before each test."""
    test_vnums = [vnum for vnum in list(obj_registry.keys()) if vnum >= 90000]
    for vnum in test_vnums:
        if vnum in obj_registry:
            del obj_registry[vnum]

    if hasattr(test_room_3001, "contents"):
        test_room_3001.contents.clear()

    yield

    test_vnums = [vnum for vnum in list(obj_registry.keys()) if vnum >= 90000]
    for vnum in test_vnums:
        if vnum in obj_registry:
            del obj_registry[vnum]

    if hasattr(test_room_3001, "contents"):
        test_room_3001.contents.clear()


_test_vnum_counter = 90000


def _get_unique_vnum() -> int:
    """Get a unique vnum for test objects."""
    global _test_vnum_counter
    _test_vnum_counter += 1
    return _test_vnum_counter


def test_put_in_pit_assigns_timer_if_none(test_room_3001):
    """
    PUT-003-1: Putting object without timer in pit assigns random timer (100-200).

    ROM C: act_obj.c:426-433
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0
    char.inventory = []

    # Create pit donation box (vnum=3010, no TAKE flag)
    pit_vnum = _get_unique_vnum()
    pit_proto = ObjIndex(
        vnum=OBJ_VNUM_PIT,  # ROM C OBJ_VNUM_PIT
        name="pit donation box",
        short_descr="the donation pit",
        description="A large pit for donated items.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=0,  # !CAN_WEAR(ITEM_TAKE)
        value=[100, 0, -1, 50, 100],  # [weight, flags, key, capacity, weight_mult]
    )
    obj_registry[pit_vnum] = pit_proto
    pit = Object(prototype=pit_proto, instance_id=None)
    test_room_3001.contents.append(pit)

    # Create object with no timer
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=0,
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    obj.timer = 0
    obj.extra_flags = 0
    obj.carried_by = char
    obj.wear_loc = -1
    char.inventory.append(obj)
    char.carry_number = 1
    char.carry_weight = 10

    # Put object in pit
    result = do_put(char, "sword pit")

    # ROM C: timer should be assigned in range [100, 200]
    assert "You put a test sword in the donation pit." in result
    assert 100 <= obj.timer <= 200, f"Expected timer 100-200, got {obj.timer}"
    # HAD_TIMER flag should NOT be set (object had no timer)
    assert not (obj.extra_flags & int(ExtraFlag.HAD_TIMER)), "HAD_TIMER should not be set"


def test_put_in_pit_preserves_timer_with_had_timer_flag(test_room_3001):
    """
    PUT-003-2: Putting object with timer in pit sets HAD_TIMER flag.

    ROM C: act_obj.c:426-433
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0
    char.inventory = []

    # Create pit donation box
    pit_vnum = _get_unique_vnum()
    pit_proto = ObjIndex(
        vnum=OBJ_VNUM_PIT,
        name="pit donation box",
        short_descr="the donation pit",
        description="A large pit for donated items.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=0,  # !CAN_WEAR(ITEM_TAKE)
        value=[100, 0, -1, 50, 100],
    )
    obj_registry[pit_vnum] = pit_proto
    pit = Object(prototype=pit_proto, instance_id=None)
    test_room_3001.contents.append(pit)

    # Create object with existing timer
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="helmet test",
        short_descr="a test helmet",
        description="A helmet for testing.",
        item_type=int(ItemType.ARMOR),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=0,
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    obj.timer = 50
    obj.extra_flags = 0
    obj.carried_by = char
    obj.wear_loc = -1
    char.inventory.append(obj)
    char.carry_number = 1
    char.carry_weight = 10

    # Put object in pit
    result = do_put(char, "helmet pit")

    # ROM C: timer should be preserved
    assert "You put a test helmet in the donation pit." in result
    assert obj.timer == 50, "Expected timer=50 preserved"
    # HAD_TIMER flag should be set
    assert obj.extra_flags & int(ExtraFlag.HAD_TIMER), "HAD_TIMER should be set"


def test_put_in_normal_container_no_timer_logic(test_room_3001):
    """
    PUT-003-3: Putting object in normal container does NOT trigger timer logic.

    Only donation pit (vnum 3010, !TAKE) should trigger timer logic.
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0
    char.inventory = []

    # Create normal container (not pit)
    container_vnum = _get_unique_vnum()
    container_proto = ObjIndex(
        vnum=container_vnum,
        name="bag sack",
        short_descr="a large sack",
        description="A large sack for carrying items.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=int(WearFlag.TAKE),  # HAS TAKE flag (not a pit)
        value=[5, 0, -1, 50, 100],
    )
    obj_registry[container_vnum] = container_proto
    container = Object(prototype=container_proto, instance_id=None)
    test_room_3001.contents.append(container)

    # Create object with no timer
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=0,
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    obj.timer = 0
    obj.extra_flags = 0
    obj.carried_by = char
    obj.wear_loc = -1
    char.inventory.append(obj)
    char.carry_number = 1
    char.carry_weight = 10

    # Put object in normal container
    result = do_put(char, "sword sack")

    # ROM C: timer should remain 0 (no pit timer logic)
    assert "You put a test sword in a large sack." in result
    assert obj.timer == 0, "Expected timer=0 (no pit logic)"
    # HAD_TIMER flag should NOT be set
    assert not (obj.extra_flags & int(ExtraFlag.HAD_TIMER)), "HAD_TIMER should not be set"


def test_put_all_in_pit_assigns_timers(test_room_3001):
    """
    PUT-003-4: 'put all pit' assigns timers to all objects without timers.

    ROM C: act_obj.c:465-472
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0
    char.inventory = []

    # Create pit donation box
    pit_vnum = _get_unique_vnum()
    pit_proto = ObjIndex(
        vnum=OBJ_VNUM_PIT,
        name="pit donation box",
        short_descr="the donation pit",
        description="A large pit for donated items.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=0,
        value=[100, 0, -1, 50, 100],
    )
    obj_registry[pit_vnum] = pit_proto
    pit = Object(prototype=pit_proto, instance_id=None)
    test_room_3001.contents.append(pit)

    # Create multiple objects without timers
    obj1_vnum = _get_unique_vnum()
    obj1_proto = ObjIndex(
        vnum=obj1_vnum,
        name="apple",
        short_descr="a red apple",
        description="A red apple.",
        item_type=int(ItemType.FOOD),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=0,
    )
    obj_registry[obj1_vnum] = obj1_proto
    obj1 = Object(prototype=obj1_proto, instance_id=None)
    obj1.timer = 0
    obj1.extra_flags = 0
    obj1.carried_by = char
    obj1.wear_loc = -1

    obj2_vnum = _get_unique_vnum()
    obj2_proto = ObjIndex(
        vnum=obj2_vnum,
        name="bread",
        short_descr="a loaf of bread",
        description="A loaf of bread.",
        item_type=int(ItemType.FOOD),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=0,
    )
    obj_registry[obj2_vnum] = obj2_proto
    obj2 = Object(prototype=obj2_proto, instance_id=None)
    obj2.timer = 0
    obj2.extra_flags = 0
    obj2.carried_by = char
    obj2.wear_loc = -1

    char.inventory.append(obj1)
    char.inventory.append(obj2)
    char.carry_number = 2
    char.carry_weight = 20

    # Put all objects in pit
    result = do_put(char, "all pit")

    # ROM C: all objects should have timers assigned
    assert "You put a red apple in the donation pit." in result
    assert "You put a loaf of bread in the donation pit." in result
    assert 100 <= obj1.timer <= 200, f"Expected obj1 timer 100-200, got {obj1.timer}"
    assert 100 <= obj2.timer <= 200, f"Expected obj2 timer 100-200, got {obj2.timer}"
    # HAD_TIMER flags should NOT be set (no original timers)
    assert not (obj1.extra_flags & int(ExtraFlag.HAD_TIMER)), "obj1 HAD_TIMER should not be set"
    assert not (obj2.extra_flags & int(ExtraFlag.HAD_TIMER)), "obj2 HAD_TIMER should not be set"


def test_put_all_in_pit_preserves_existing_timers(test_room_3001):
    """
    PUT-003-5: 'put all pit' sets HAD_TIMER flag on objects with existing timers.

    ROM C: act_obj.c:465-472
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0
    char.inventory = []

    # Create pit donation box
    pit_vnum = _get_unique_vnum()
    pit_proto = ObjIndex(
        vnum=OBJ_VNUM_PIT,
        name="pit donation box",
        short_descr="the donation pit",
        description="A large pit for donated items.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=0,
        value=[100, 0, -1, 50, 100],
    )
    obj_registry[pit_vnum] = pit_proto
    pit = Object(prototype=pit_proto, instance_id=None)
    test_room_3001.contents.append(pit)

    # Create objects with existing timers
    obj1_vnum = _get_unique_vnum()
    obj1_proto = ObjIndex(
        vnum=obj1_vnum,
        name="potion",
        short_descr="a healing potion",
        description="A healing potion.",
        item_type=int(ItemType.POTION),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=0,
    )
    obj_registry[obj1_vnum] = obj1_proto
    obj1 = Object(prototype=obj1_proto, instance_id=None)
    obj1.timer = 30
    obj1.extra_flags = 0
    obj1.carried_by = char
    obj1.wear_loc = -1

    obj2_vnum = _get_unique_vnum()
    obj2_proto = ObjIndex(
        vnum=obj2_vnum,
        name="scroll",
        short_descr="a magic scroll",
        description="A magic scroll.",
        item_type=int(ItemType.SCROLL),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=0,
    )
    obj_registry[obj2_vnum] = obj2_proto
    obj2 = Object(prototype=obj2_proto, instance_id=None)
    obj2.timer = 20
    obj2.extra_flags = 0
    obj2.carried_by = char
    obj2.wear_loc = -1

    char.inventory.append(obj1)
    char.inventory.append(obj2)
    char.carry_number = 2
    char.carry_weight = 20

    # Put all objects in pit
    result = do_put(char, "all pit")

    # ROM C: timers should be preserved
    assert "You put a healing potion in the donation pit." in result
    assert "You put a magic scroll in the donation pit." in result
    assert obj1.timer == 30, "Expected obj1 timer=30 preserved"
    assert obj2.timer == 20, "Expected obj2 timer=20 preserved"
    # HAD_TIMER flags should be set
    assert obj1.extra_flags & int(ExtraFlag.HAD_TIMER), "obj1 HAD_TIMER should be set"
    assert obj2.extra_flags & int(ExtraFlag.HAD_TIMER), "obj2 HAD_TIMER should be set"


def test_pit_identification_requires_vnum_and_no_take_flag(test_room_3001):
    """
    PUT-003-6: Pit identification requires both vnum 3010 AND !TAKE flag.

    A container with vnum 3010 but WITH TAKE flag is not a donation pit.
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0
    char.inventory = []

    # Create a takeable container with pit vnum (not a real pit)
    fake_pit_vnum = _get_unique_vnum()
    fake_pit_proto = ObjIndex(
        vnum=OBJ_VNUM_PIT,  # Same vnum as real pit
        name="pit fake",
        short_descr="a fake pit",
        description="A fake pit.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=int(WearFlag.TAKE),  # HAS TAKE flag (not a real pit)
        value=[100, 0, -1, 50, 100],
    )
    obj_registry[fake_pit_vnum] = fake_pit_proto
    fake_pit = Object(prototype=fake_pit_proto, instance_id=None)
    test_room_3001.contents.append(fake_pit)

    # Create object with no timer
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=0,
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    obj.timer = 0
    obj.extra_flags = 0
    obj.carried_by = char
    obj.wear_loc = -1
    char.inventory.append(obj)
    char.carry_number = 1
    char.carry_weight = 10

    # Put object in fake pit
    result = do_put(char, "sword pit")

    # ROM C: timer should NOT be assigned (not a real donation pit)
    assert "You put a test sword in a fake pit." in result
    assert obj.timer == 0, "Expected timer=0 (not a real pit)"
    # HAD_TIMER flag should NOT be set
    assert not (obj.extra_flags & int(ExtraFlag.HAD_TIMER)), "HAD_TIMER should not be set"
