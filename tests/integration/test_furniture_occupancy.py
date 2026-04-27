"""Integration tests for GET-008: Furniture occupancy check.

ROM Parity References:
- src/act_obj.c:126-134 (furniture occupancy check in get_obj helper)

This test suite verifies that QuickMUD prevents taking objects that someone is
sitting/standing on, matching ROM 2.4b6 behavior.

ROM C Reference:
    for (gch = obj->in_room->people; gch != NULL; gch = gch->next_in_room)
        if (gch->on == obj)
        {
            act ("$N appears to be using $p.", ch, obj, gch, TO_CHAR);
            return;
        }
"""

from __future__ import annotations

import pytest

from mud.commands.inventory import do_get
from mud.models.constants import ItemType, Position, WearFlag
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


def create_chair(vnum: int | None = None) -> Object:
    """Create a chair furniture object."""
    if vnum is None:
        vnum = _get_unique_vnum()
    proto = ObjIndex(
        vnum=vnum,
        name="chair wooden",
        short_descr="a wooden chair",
        description="A sturdy wooden chair sits here.",
        item_type=int(ItemType.FURNITURE),
        wear_flags=int(WearFlag.TAKE),
        value=[5, 250, 0, 0, 0],
    )
    obj_registry[vnum] = proto
    return Object(instance_id=vnum, prototype=proto)


def create_table(vnum: int | None = None) -> Object:
    """Create a table container object (non-furniture but can be stood on)."""
    if vnum is None:
        vnum = _get_unique_vnum()
    proto = ObjIndex(
        vnum=vnum,
        name="table wooden",
        short_descr="a wooden table",
        description="A sturdy wooden table sits here.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=int(WearFlag.TAKE),
        value=[100, 0, 1003, 0, 0],
    )
    obj_registry[vnum] = proto
    return Object(instance_id=vnum, prototype=proto)


def test_get_furniture_with_someone_sitting_on_it(movable_char_factory, test_room_3001):
    """
    Test that you cannot take furniture if someone is sitting on it.

    ROM C Reference: src/act_obj.c lines 126-134
    Expected: "$N appears to be using $p." message, object not taken
    """
    char = movable_char_factory(name="Player", room_vnum=3001)

    chair = create_chair()
    test_room_3001.add_object(chair)

    other_char = movable_char_factory(name="Bob", room_vnum=3001)
    other_char.position = Position.SITTING
    other_char.on = chair

    result = do_get(char, "chair")

    assert result is not None, "Should return error message"
    assert "appears to be using" in result.lower(), f"Expected furniture occupancy message, got: {result}"
    assert "chair" in result.lower() or "it" in result.lower(), f"Expected object name in message, got: {result}"

    assert chair not in char.inventory, "Chair should not be in player inventory"


def test_get_furniture_with_someone_standing_on_it(movable_char_factory, test_room_3001):
    """
    Test that you cannot take furniture if someone is standing on it.

    ROM C Reference: src/act_obj.c lines 126-134
    The check is position-agnostic - any character with on=obj prevents taking.
    """
    char = movable_char_factory(name="Player", room_vnum=3001)

    chair = create_chair()
    test_room_3001.add_object(chair)

    other_char = movable_char_factory(name="Bob", room_vnum=3001)
    other_char.position = Position.STANDING
    other_char.on = chair

    result = do_get(char, "chair")

    assert result is not None, "Should return error message"
    assert "appears to be using" in result.lower(), f"Expected furniture occupancy message, got: {result}"


def test_get_furniture_with_no_one_on_it(movable_char_factory, test_room_3001):
    """
    Test that you CAN take furniture if no one is using it.

    ROM C Reference: src/act_obj.c lines 126-134
    The loop should complete without finding anyone on the object.
    """
    char = movable_char_factory(name="Player", room_vnum=3001)

    chair = create_chair()
    test_room_3001.add_object(chair)

    result = do_get(char, "chair")

    if result:
        assert "appears to be using" not in result.lower(), f"Should not block taking, got: {result}"
        assert "you get" in result.lower() or "you take" in result.lower() or "chair" in result.lower(), (
            f"Expected success message, got: {result}"
        )

    assert chair in char.inventory, "Chair should be in player inventory"


def test_get_furniture_with_someone_nearby_but_not_on_it(movable_char_factory, test_room_3001):
    """
    Test that you CAN take furniture if someone is in the room but not ON it.

    ROM C Reference: src/act_obj.c lines 126-134
    The check is specifically: if (gch->on == obj)
    Being in the same room is not sufficient.
    """
    char = movable_char_factory(name="Player", room_vnum=3001)

    chair = create_chair()
    test_room_3001.add_object(chair)

    other_char = movable_char_factory(name="Bob", room_vnum=3001)
    other_char.position = Position.STANDING
    other_char.on = None

    result = do_get(char, "chair")

    if result:
        assert "appears to be using" not in result.lower(), f"Should not block taking when not on object, got: {result}"


def test_get_furniture_multiple_people_on_it(movable_char_factory, test_room_3001):
    """
    Test furniture occupancy check with multiple people on the same object.

    ROM C Reference: src/act_obj.c lines 126-134
    The loop breaks on first match, but any match prevents taking.
    """
    char = movable_char_factory(name="Player", room_vnum=3001)

    chair = create_chair()
    test_room_3001.add_object(chair)

    char1 = movable_char_factory(name="Bob", room_vnum=3001)
    char1.position = Position.SITTING
    char1.on = chair

    char2 = movable_char_factory(name="Alice", room_vnum=3001)
    char2.position = Position.SITTING
    char2.on = chair

    result = do_get(char, "chair")

    assert result is not None, "Should return error message"
    assert "appears to be using" in result.lower(), f"Expected furniture occupancy message, got: {result}"


def test_get_non_furniture_with_someone_on_it(movable_char_factory, test_room_3001):
    """
    Test that occupancy check applies to ANY object type, not just ITEM_FURNITURE.

    ROM C Reference: src/act_obj.c lines 126-134
    The check is done for ANY object in room, regardless of item_type.
    """
    char = movable_char_factory(name="Player", room_vnum=3001)

    table = create_table()
    test_room_3001.add_object(table)

    other_char = movable_char_factory(name="Bob", room_vnum=3001)
    other_char.position = Position.STANDING
    other_char.on = table

    result = do_get(char, "table")

    assert result is not None, "Should return error message"
    assert "appears to be using" in result.lower(), f"Expected furniture occupancy message, got: {result}"
