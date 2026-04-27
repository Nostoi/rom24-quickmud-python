"""Integration tests for PUT-002: WEIGHT_MULT check for containers in containers.

ROM Parity References:
- src/act_obj.c:411-416 (single put), 458 (put all) - WEIGHT_MULT != 100 check

This test suite verifies that QuickMUD prevents putting containers into containers
(WEIGHT_MULT != 100), matching ROM 2.4b6 behavior.

ROM C Reference (single put):
    if (WEIGHT_MULT(obj) != 100)
    {
        send_to_char("You have a feeling that would be a bad idea.\\n\\r", ch);
        return;
    }

ROM C Reference (put all):
    && WEIGHT_MULT(obj) == 100  // Only put non-containers
"""

from __future__ import annotations

import pytest

from mud.commands.obj_manipulation import do_put
from mud.models.constants import ItemType
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


def test_cannot_put_container_in_container(test_room_3001):
    """
    PUT-002-1: Cannot put container with WEIGHT_MULT != 100 into another container.

    ROM C: act_obj.c:411-416
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.location = test_room_3001
    char.level = 5
    char.inventory = []
    char.carry_weight = 0
    char.carry_number = 0

    # Create large bag (target container)
    large_bag_vnum = _get_unique_vnum()
    large_bag_proto = ObjIndex(
        vnum=large_bag_vnum,
        name="bag large",
        short_descr="a large bag",
        description="A large bag lies here.",
        item_type=ItemType.CONTAINER,
        wear_flags=1,
        value=[1000, 0, 0, 1000, 100],  # WEIGHT_MULT = 100 (normal)
    )
    obj_registry[large_bag_vnum] = large_bag_proto
    large_bag = Object(prototype=large_bag_proto, instance_id=None)
    large_bag.value = large_bag_proto.value
    large_bag.location = test_room_3001
    large_bag.contained_items = []
    test_room_3001.contents = [large_bag]

    # Create small bag (container with WEIGHT_MULT = 50, trying to put inside)
    small_bag_vnum = _get_unique_vnum()
    small_bag_proto = ObjIndex(
        vnum=small_bag_vnum,
        name="bag small",
        short_descr="a small bag",
        description="A small bag lies here.",
        item_type=ItemType.CONTAINER,
        wear_flags=1,
        value=[100, 0, 0, 100, 50],  # WEIGHT_MULT = 50 (magic bag - reduces weight)
    )
    obj_registry[small_bag_vnum] = small_bag_proto
    small_bag = Object(prototype=small_bag_proto, instance_id=None)
    small_bag.value = small_bag_proto.value
    small_bag.carried_by = char
    small_bag.wear_loc = -1
    small_bag.contained_items = []
    char.inventory.append(small_bag)
    char.carry_number = 1
    char.carry_weight = 20

    # Try to put small bag in large bag
    result = do_put(char, "small large")

    # Verify error message
    assert "bad idea" in result.lower()

    # Verify small bag NOT transferred
    assert small_bag in char.inventory
    assert small_bag not in large_bag.contained_items


def test_can_put_normal_object_with_weight_mult_100(test_room_3001):
    """
    PUT-002-2: CAN put normal objects (WEIGHT_MULT = 100) into containers.

    ROM C: act_obj.c:411-416 - check only fails if WEIGHT_MULT != 100
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.location = test_room_3001
    char.level = 5
    char.inventory = []
    char.carry_weight = 0
    char.carry_number = 0

    # Create bag container
    bag_vnum = _get_unique_vnum()
    bag_proto = ObjIndex(
        vnum=bag_vnum,
        name="bag",
        short_descr="a leather bag",
        description="A leather bag lies here.",
        item_type=ItemType.CONTAINER,
        wear_flags=1,
        value=[100, 0, 0, 100, 100],
    )
    obj_registry[bag_vnum] = bag_proto
    bag = Object(prototype=bag_proto, instance_id=None)
    bag.value = bag_proto.value
    bag.location = test_room_3001
    bag.contained_items = []
    test_room_3001.contents = [bag]

    # Create sword (WEAPON - not a container, WEIGHT_MULT = 100)
    sword_vnum = _get_unique_vnum()
    sword_proto = ObjIndex(
        vnum=sword_vnum,
        name="sword",
        short_descr="a steel sword",
        description="A steel sword lies here.",
        item_type=ItemType.WEAPON,
        wear_flags=1,
        weight=50,
    )
    obj_registry[sword_vnum] = sword_proto
    sword = Object(prototype=sword_proto, instance_id=None)
    sword.carried_by = char
    sword.wear_loc = -1
    char.inventory.append(sword)
    char.carry_number = 1
    char.carry_weight = 50

    # Put sword in bag (should succeed - WEIGHT_MULT = 100)
    result = do_put(char, "sword bag")

    # Verify success
    assert "you put" in result.lower()
    assert sword in bag.contained_items
    assert sword not in char.inventory


def test_put_all_skips_containers(test_room_3001):
    """
    PUT-002-3: "put all" skips containers (WEIGHT_MULT != 100).

    ROM C: act_obj.c:458 - && WEIGHT_MULT(obj) == 100
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.location = test_room_3001
    char.level = 5
    char.inventory = []
    char.carry_weight = 0
    char.carry_number = 0

    # Create target bag
    target_bag_vnum = _get_unique_vnum()
    target_bag_proto = ObjIndex(
        vnum=target_bag_vnum,
        name="bag target",
        short_descr="a target bag",
        description="A target bag lies here.",
        item_type=ItemType.CONTAINER,
        wear_flags=1,
        value=[1000, 0, 0, 1000, 100],
    )
    obj_registry[target_bag_vnum] = target_bag_proto
    target_bag = Object(prototype=target_bag_proto, instance_id=None)
    target_bag.value = target_bag_proto.value
    target_bag.location = test_room_3001
    target_bag.contained_items = []
    test_room_3001.contents = [target_bag]

    # Create items to carry:
    # 1. Sword (WEIGHT_MULT = 100, should be put)
    sword_vnum = _get_unique_vnum()
    sword_proto = ObjIndex(
        vnum=sword_vnum,
        name="sword",
        short_descr="a steel sword",
        description="A steel sword lies here.",
        item_type=ItemType.WEAPON,
        wear_flags=1,
        weight=50,
    )
    obj_registry[sword_vnum] = sword_proto
    sword = Object(prototype=sword_proto, instance_id=None)
    sword.carried_by = char
    sword.wear_loc = -1
    char.inventory.append(sword)

    # 2. Pouch (container with WEIGHT_MULT = 75, should be skipped)
    pouch_vnum = _get_unique_vnum()
    pouch_proto = ObjIndex(
        vnum=pouch_vnum,
        name="pouch",
        short_descr="a belt pouch",
        description="A belt pouch lies here.",
        item_type=ItemType.CONTAINER,
        wear_flags=1,
        value=[50, 0, 0, 50, 75],  # WEIGHT_MULT = 75
    )
    obj_registry[pouch_vnum] = pouch_proto
    pouch = Object(prototype=pouch_proto, instance_id=None)
    pouch.value = pouch_proto.value
    pouch.carried_by = char
    pouch.wear_loc = -1
    pouch.contained_items = []
    char.inventory.append(pouch)

    # 3. Shield (WEIGHT_MULT = 100, should be put)
    shield_vnum = _get_unique_vnum()
    shield_proto = ObjIndex(
        vnum=shield_vnum,
        name="shield",
        short_descr="a wooden shield",
        description="A wooden shield lies here.",
        item_type=ItemType.ARMOR,
        wear_flags=1,
        weight=30,
    )
    obj_registry[shield_vnum] = shield_proto
    shield = Object(prototype=shield_proto, instance_id=None)
    shield.carried_by = char
    shield.wear_loc = -1
    char.inventory.append(shield)

    char.carry_number = 3
    char.carry_weight = 100

    # Execute "put all target"
    result = do_put(char, "all target")

    # Verify sword and shield transferred (WEIGHT_MULT = 100)
    assert sword in target_bag.contained_items
    assert shield in target_bag.contained_items

    # Verify pouch NOT transferred (WEIGHT_MULT = 75)
    assert pouch in char.inventory
    assert pouch not in target_bag.contained_items

    # Result should show 2 put actions (sword + shield)
    put_count = result.lower().count("you put")
    assert put_count == 2, f"Expected 2 'you put' messages, got {put_count}"


def test_weight_mult_100_is_allowed(test_room_3001):
    """
    PUT-002-4: Containers with WEIGHT_MULT = 100 (normal bags) ARE allowed.

    ROM C: act_obj.c:411 - check is (WEIGHT_MULT(obj) != 100)
    """
    from mud.models.character import Character

    # Create test character
    char = Character(name="TestChar", is_npc=False, race=0, ch_class=0)
    char.room = test_room_3001
    char.location = test_room_3001
    char.level = 5
    char.inventory = []
    char.carry_weight = 0
    char.carry_number = 0

    # Create chest (target container)
    chest_vnum = _get_unique_vnum()
    chest_proto = ObjIndex(
        vnum=chest_vnum,
        name="chest",
        short_descr="a wooden chest",
        description="A wooden chest sits here.",
        item_type=ItemType.CONTAINER,
        wear_flags=1,
        value=[500, 0, 0, 500, 100],
    )
    obj_registry[chest_vnum] = chest_proto
    chest = Object(prototype=chest_proto, instance_id=None)
    chest.value = chest_proto.value
    chest.location = test_room_3001
    chest.contained_items = []
    test_room_3001.contents = [chest]

    # Create normal bag (WEIGHT_MULT = 100, should be allowed)
    normal_bag_vnum = _get_unique_vnum()
    normal_bag_proto = ObjIndex(
        vnum=normal_bag_vnum,
        name="bag",
        short_descr="a normal bag",
        description="A normal bag lies here.",
        item_type=ItemType.CONTAINER,
        wear_flags=1,
        value=[100, 0, 0, 100, 100],  # WEIGHT_MULT = 100 (normal, no weight reduction)
    )
    obj_registry[normal_bag_vnum] = normal_bag_proto
    normal_bag = Object(prototype=normal_bag_proto, instance_id=None)
    normal_bag.value = normal_bag_proto.value
    normal_bag.carried_by = char
    normal_bag.wear_loc = -1
    normal_bag.contained_items = []
    char.inventory.append(normal_bag)
    char.carry_number = 1
    char.carry_weight = 20

    # Try to put normal bag in chest (should succeed - WEIGHT_MULT = 100)
    result = do_put(char, "bag chest")

    # Verify success
    assert "you put" in result.lower()
    assert normal_bag in chest.contained_items
    assert normal_bag not in char.inventory
