"""Integration tests for GET-012: Numbered object syntax support.

ROM Parity References:
- src/act_obj.c:222 (get_obj_list usage for numbered syntax)

This test suite verifies that QuickMUD supports numbered object syntax
(e.g., "get 2.sword" to get second sword) using get_obj_list(), matching ROM 2.4b6 behavior.

ROM C Reference:
    obj = get_obj_list(ch, arg1, ch->in_room->contents);

get_obj_list() supports syntax like "2.sword" to get the second sword.
"""

from __future__ import annotations

import pytest

from mud.commands.inventory import do_get
from mud.models.constants import ItemType, WearFlag
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


def test_get_second_sword_from_room(test_room_3001):
    """
    GET-012-1: "get 2.sword" retrieves second sword from room.

    ROM C: act_obj.c:222 (get_obj_list with numbered syntax)
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0

    # Create three swords in room
    swords = []
    for i in range(1, 4):
        obj_vnum = _get_unique_vnum()
        obj_proto = ObjIndex(
            vnum=obj_vnum,
            name=f"sword test{i}",
            short_descr=f"test sword #{i}",
            description=f"The #{i} test sword.",
            item_type=int(ItemType.WEAPON),
            wear_flags=int(WearFlag.TAKE),
        )
        obj_registry[obj_vnum] = obj_proto
        obj = Object(prototype=obj_proto, instance_id=None)
        test_room_3001.contents.append(obj)
        swords.append(obj)

    # Get second sword using numbered syntax
    result = do_get(char, "2.sword")

    # ROM C: Should retrieve the second sword (index 1)
    assert "You get" in result
    assert "#2" in result, "Expected second sword to be retrieved"

    # Verify second sword was taken (not first or third)
    assert swords[1] not in test_room_3001.contents, "Second sword should be removed from room"
    assert swords[0] in test_room_3001.contents, "First sword should remain in room"
    assert swords[2] in test_room_3001.contents, "Third sword should remain in room"


def test_get_third_potion_from_container(test_room_3001):
    """
    GET-012-2: "get 3.potion container" retrieves third potion from container.

    ROM C: get_obj_list works for container contents too
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0

    # Create container in room
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

    # Create four potions in container
    potions = []
    for i in range(1, 5):
        obj_vnum = _get_unique_vnum()
        obj_proto = ObjIndex(
            vnum=obj_vnum,
            name=f"potion healing{i}",
            short_descr=f"healing potion #{i}",
            description=f"The #{i} healing potion.",
            item_type=int(ItemType.POTION),
            wear_flags=int(WearFlag.TAKE),
        )
        obj_registry[obj_vnum] = obj_proto
        obj = Object(prototype=obj_proto, instance_id=None)
        potions.append(obj)

    container.contained_items = potions

    # Remember which potion should be removed (third one, index 2)
    third_potion_vnum = potions[2].prototype.vnum

    # Get third potion using numbered syntax
    result = do_get(char, "3.potion backpack")

    # ROM C: Should retrieve the third potion (index 2)
    assert "You get" in result
    assert "#3" in result, "Expected third potion to be retrieved"

    # Verify third potion was taken (not others)
    assert len(container.contained_items) == 3, "Should have 3 potions left (removed 1 of 4)"
    remaining_vnums = {obj.prototype.vnum for obj in container.contained_items}
    assert third_potion_vnum not in remaining_vnums, "Third potion should be removed from container"


def test_get_first_object_without_number(test_room_3001):
    """
    GET-012-3: "get sword" (no number) retrieves first sword.

    ROM C: get_obj_list defaults to 1 when no number specified
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0

    # Create three swords in room
    swords = []
    for i in range(1, 4):
        obj_vnum = _get_unique_vnum()
        obj_proto = ObjIndex(
            vnum=obj_vnum,
            name=f"sword test{i}",
            short_descr=f"test sword #{i}",
            description=f"The #{i} test sword.",
            item_type=int(ItemType.WEAPON),
            wear_flags=int(WearFlag.TAKE),
        )
        obj_registry[obj_vnum] = obj_proto
        obj = Object(prototype=obj_proto, instance_id=None)
        test_room_3001.contents.append(obj)
        swords.append(obj)

    # Get sword without number (defaults to first)
    result = do_get(char, "sword")

    # ROM C: Should retrieve the first sword (index 0)
    assert "You get" in result
    assert "#1" in result, "Expected first sword to be retrieved"

    # Verify first sword was taken
    assert swords[0] not in test_room_3001.contents, "First sword should be removed from room"
    assert swords[1] in test_room_3001.contents, "Second sword should remain in room"
    assert swords[2] in test_room_3001.contents, "Third sword should remain in room"


def test_get_nonexistent_numbered_object(test_room_3001):
    """
    GET-012-4: "get 5.sword" fails when only 3 swords exist.

    ROM C: get_obj_list returns NULL when number exceeds matches
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.level = 5
    char.gold = 0
    char.silver = 0

    # Create only three swords in room
    for i in range(1, 4):
        obj_vnum = _get_unique_vnum()
        obj_proto = ObjIndex(
            vnum=obj_vnum,
            name=f"sword test{i}",
            short_descr=f"test sword #{i}",
            description=f"The #{i} test sword.",
            item_type=int(ItemType.WEAPON),
            wear_flags=int(WearFlag.TAKE),
        )
        obj_registry[obj_vnum] = obj_proto
        obj = Object(prototype=obj_proto, instance_id=None)
        test_room_3001.contents.append(obj)

    # Try to get fifth sword (doesn't exist)
    result = do_get(char, "5.sword")

    # ROM C: Should fail with "I see no X here" message
    assert "I see no" in result or "You don't see" in result, "Expected error message for nonexistent object"

    # Verify all swords remain in room
    assert len(test_room_3001.contents) == 3, "All swords should remain in room"
