"""Integration tests for GET-010: Pit timer handling.

ROM Parity References:
- src/act_obj.c:146-149, 152 (pit timer handling in get_obj helper)

This test suite verifies that QuickMUD handles ITEM_HAD_TIMER flag correctly
when getting objects from the donation pit, matching ROM 2.4b6 behavior.

ROM C Reference:
    if (container->pIndexData->vnum == OBJ_VNUM_PIT
        && !CAN_WEAR(container, ITEM_TAKE)
        && !IS_OBJ_STAT(obj, ITEM_HAD_TIMER))
        obj->timer = 0;

    REMOVE_BIT(obj->extra_flags, ITEM_HAD_TIMER);
"""

from __future__ import annotations

import pytest

from mud.commands.inventory import do_get
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


def test_pit_donation_sets_timer_to_zero_without_had_timer(test_room_3001):
    """
    GET-010-1: Objects without HAD_TIMER flag get timer=0 from pit donation box.

    ROM C: act_obj.c:146-149
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0

    # Create pit donation box (vnum=3010, no TAKE flag)
    pit_vnum = _get_unique_vnum()
    pit_proto = ObjIndex(
        vnum=OBJ_VNUM_PIT,  # ROM C OBJ_VNUM_PIT
        name="pit donation box",
        short_descr="the donation pit",
        description="A large pit for donated items.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=0,  # !CAN_WEAR(ITEM_TAKE)
    )
    obj_registry[pit_vnum] = pit_proto
    pit = Object(prototype=pit_proto, instance_id=None)
    test_room_3001.contents.append(pit)

    # Create object with timer=100, no HAD_TIMER flag
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=0,  # No HAD_TIMER
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    obj.timer = 100  # Set non-zero timer
    obj.extra_flags = 0  # No HAD_TIMER
    pit.contained_items = [obj]

    # Get object from pit
    result = do_get(char, "sword pit")

    # ROM C: timer should be set to 0
    assert obj.timer == 0, "Expected timer=0 for object from pit without HAD_TIMER"
    assert "You get" in result


def test_pit_donation_preserves_timer_with_had_timer(test_room_3001):
    """
    GET-010-2: Objects with HAD_TIMER flag keep their timer from pit donation box.

    ROM C: act_obj.c:146-149 (negated condition)
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0

    # Create pit donation box (vnum=3010, no TAKE flag)
    pit_vnum = _get_unique_vnum()
    pit_proto = ObjIndex(
        vnum=OBJ_VNUM_PIT,  # ROM C OBJ_VNUM_PIT
        name="pit donation box",
        short_descr="the donation pit",
        description="A large pit for donated items.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=0,  # !CAN_WEAR(ITEM_TAKE)
    )
    obj_registry[pit_vnum] = pit_proto
    pit = Object(prototype=pit_proto, instance_id=None)
    test_room_3001.contents.append(pit)

    # Create object with timer=100 and HAD_TIMER flag
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=int(ExtraFlag.HAD_TIMER),
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    obj.timer = 100  # Set non-zero timer
    obj.extra_flags = int(ExtraFlag.HAD_TIMER)
    pit.contained_items = [obj]

    # Get object from pit
    result = do_get(char, "sword pit")

    # ROM C: timer should be preserved (not set to 0)
    assert obj.timer == 100, "Expected timer=100 for object from pit with HAD_TIMER"
    assert "You get" in result


def test_had_timer_flag_removed_after_get_from_container(test_room_3001):
    """
    GET-010-3: ITEM_HAD_TIMER flag is removed after getting from any container.

    ROM C: act_obj.c:152
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0

    # Create regular container (not pit)
    container_vnum = _get_unique_vnum()
    container_proto = ObjIndex(
        vnum=container_vnum,
        name="bag backpack",
        short_descr="a leather backpack",
        description="A sturdy leather backpack.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=int(WearFlag.TAKE),
    )
    obj_registry[container_vnum] = container_proto
    container = Object(prototype=container_proto, instance_id=None)
    test_room_3001.contents.append(container)

    # Create object with HAD_TIMER flag
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
        extra_flags=int(ExtraFlag.HAD_TIMER),
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    obj.extra_flags = int(ExtraFlag.HAD_TIMER)
    container.contained_items = [obj]

    # Get object from container
    result = do_get(char, "sword backpack")

    # ROM C: HAD_TIMER flag should be removed
    assert not (obj.extra_flags & int(ExtraFlag.HAD_TIMER)), "Expected HAD_TIMER flag removed"
    assert "You get" in result


def test_normal_container_does_not_reset_timer(test_room_3001):
    """
    GET-010-4: Normal containers don't reset timer (only pit donation box does).

    ROM C: act_obj.c:146-149 (condition check)
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0

    # Create regular container (not pit)
    container_vnum = _get_unique_vnum()
    container_proto = ObjIndex(
        vnum=container_vnum,
        name="bag backpack",
        short_descr="a leather backpack",
        description="A sturdy leather backpack.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=int(WearFlag.TAKE),
    )
    obj_registry[container_vnum] = container_proto
    container = Object(prototype=container_proto, instance_id=None)
    test_room_3001.contents.append(container)

    # Create object with timer=100, no HAD_TIMER
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
    obj.timer = 100
    obj.extra_flags = 0
    container.contained_items = [obj]

    # Get object from regular container
    result = do_get(char, "sword backpack")

    # ROM C: timer should NOT be reset (only pit resets timer)
    assert obj.timer == 100, "Expected timer=100 for object from regular container"
    assert "You get" in result
