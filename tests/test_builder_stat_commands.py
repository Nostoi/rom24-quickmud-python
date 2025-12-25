from __future__ import annotations

import pytest

from mud.commands.build import cmd_goto, cmd_mstat, cmd_ostat, cmd_rstat, cmd_vlist
from mud.models.area import Area
from mud.models.constants import LEVEL_HERO, RoomFlag, Sector, Sex
from mud.models.mob import MobIndex, mob_registry
from mud.models.obj import ObjIndex, obj_index_registry
from mud.models.room import Exit, ExtraDescr, Room
from mud.net.session import Session
from mud.registry import area_registry, room_registry


@pytest.fixture(autouse=True, scope="function")
def isolate_registries():
    """Clear registries before each test to prevent pollution from OLC tests."""
    room_registry.clear()
    mob_registry.clear()
    obj_index_registry.clear()
    area_registry.clear()
    yield


@pytest.fixture
def test_area():
    """Create a test area with rooms, mobs, and objects."""
    area = Area(
        vnum=1,
        name="Test Area",
        file_name="test.are",
        min_vnum=1000,
        max_vnum=1099,
        security=5,
        builders="testbuilder",
    )
    area_registry[1] = area
    yield area
    area_registry.pop(1, None)


@pytest.fixture
def test_room(test_area):
    """Create a test room with various properties."""
    room = Room(
        vnum=1001,
        name="Test Room",
        description="A test room for testing.",
        sector_type=Sector.INSIDE,
        room_flags=int(RoomFlag.ROOM_SAFE),
        heal_rate=150,
        mana_rate=120,
        owner="TestOwner",
        area=test_area,
    )

    # Add an exit
    exit_north = Exit(
        vnum=1002,
        keyword="door",
        description="A wooden door",
        exit_info=1,  # ISDOOR
    )
    room.exits = [exit_north, None, None, None, None, None]

    # Add extra description
    extra = ExtraDescr(keyword="painting", description="A beautiful painting hangs here.")
    room.extra_descr = [extra]

    room_registry[1001] = room
    yield room
    room_registry.pop(1001, None)


@pytest.fixture
def test_object(test_area):
    """Create a test object prototype."""
    obj = ObjIndex(
        vnum=1050,
        name="sword weapon blade",
        short_descr="a gleaming sword",
        description="A gleaming sword lies here.",
        item_type="weapon",
        level=10,
        weight=8,
        cost=100,
        material="steel",
        value=[0, 2, 8, 1, 0],
        area=test_area,
    )
    obj.extra_descr = [{"keyword": "runes", "description": "Ancient runes glow faintly."}]
    obj.affects = [{"location": "hitroll", "modifier": 2}]
    obj_index_registry[1050] = obj
    yield obj
    obj_index_registry.pop(1050, None)


@pytest.fixture
def test_mobile(test_area):
    """Create a test mobile prototype."""
    mob = MobIndex(
        vnum=1025,
        player_name="guard soldier",
        short_descr="a city guard",
        long_descr="A city guard stands here.",
        description="He wears chainmail and carries a sword.",
        level=15,
        alignment=500,
        hitroll=10,
        race="human",
        sex=Sex.MALE,
        wealth=200,
        hit_dice="15d8+50",
        mana_dice="100d10+0",
        damage_dice="2d6+3",
        damage_type="slash",
        ac="10d1+0",
        area=test_area,
    )
    mob_registry[1025] = mob
    yield mob
    mob_registry.pop(1025, None)


@pytest.fixture
def builder_char(test_room):
    """Create a character with builder privileges."""
    from mud.models.character import Character

    char = Character()
    char.name = "TestBuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.room = test_room
    char.pcdata = type("PCData", (), {"security": 9})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


# @rstat tests


def test_rstat_current_room(builder_char, test_room):
    result = cmd_rstat(builder_char, "")

    assert "Room: Test Room" in result
    assert "Vnum: 1001" in result
    assert "A test room for testing" in result
    assert "Area: Test Area" in result
    assert "Sector: inside" in result
    assert "safe" in result
    assert "Heal rate: 150" in result
    assert "Mana rate: 120" in result
    assert "Owner: TestOwner" in result


def test_rstat_shows_exits(builder_char, test_room):
    result = cmd_rstat(builder_char, "")

    assert "Exits:" in result
    assert "north: 1002" in result
    assert "door" in result


def test_rstat_shows_extra_descriptions(builder_char, test_room):
    result = cmd_rstat(builder_char, "")

    assert "Extra descriptions:" in result
    assert "painting" in result


def test_rstat_specific_room(builder_char, test_room):
    result = cmd_rstat(builder_char, "1001")

    assert "Room: Test Room" in result
    assert "Vnum: 1001" in result


def test_rstat_invalid_vnum(builder_char):
    result = cmd_rstat(builder_char, "abc")
    assert "Room vnum must be a number" in result


def test_rstat_nonexistent_room(builder_char):
    result = cmd_rstat(builder_char, "9999")
    assert "No room with vnum 9999" in result


def test_rstat_no_room(builder_char):
    builder_char.room = None
    result = cmd_rstat(builder_char, "")
    assert "You are not in a room" in result


# @ostat tests


def test_ostat_shows_object_details(builder_char, test_object):
    result = cmd_ostat(builder_char, "1050")

    assert "Object: a gleaming sword" in result
    assert "Vnum: 1050" in result
    assert "Name: sword weapon blade" in result
    assert "Short: a gleaming sword" in result
    assert "Long: A gleaming sword lies here" in result
    assert "Type: weapon" in result
    assert "Level: 10" in result
    assert "Weight: 8" in result
    assert "Cost: 100" in result
    assert "Material: steel" in result
    assert "Values: 0 2 8 1 0" in result
    assert "Area: Test Area" in result


def test_ostat_shows_extra_descriptions(builder_char, test_object):
    result = cmd_ostat(builder_char, "1050")

    assert "Extra descriptions: 1" in result
    assert "runes" in result


def test_ostat_shows_affects(builder_char, test_object):
    result = cmd_ostat(builder_char, "1050")

    assert "Affects: 1" in result
    assert "hitroll" in result
    assert "+2" in result


def test_ostat_requires_vnum(builder_char):
    result = cmd_ostat(builder_char, "")
    assert "Syntax: @ostat <vnum>" in result


def test_ostat_invalid_vnum(builder_char):
    result = cmd_ostat(builder_char, "abc")
    assert "Object vnum must be a number" in result


def test_ostat_nonexistent_object(builder_char):
    result = cmd_ostat(builder_char, "9999")
    assert "No object prototype with vnum 9999" in result


# @mstat tests


def test_mstat_shows_mobile_details(builder_char, test_mobile):
    result = cmd_mstat(builder_char, "1025")

    assert "Mobile: a city guard" in result
    assert "Vnum: 1025" in result
    assert "Name: guard soldier" in result
    assert "Short: a city guard" in result
    assert "Long: A city guard stands here" in result
    assert "Description: He wears chainmail and carries a sword" in result
    assert "Level: 15" in result
    assert "Alignment: 500" in result
    assert "Hitroll: 10" in result
    assert "Race: human" in result
    assert "Sex: male" in result
    assert "Wealth: 200" in result
    assert "Hit dice: 15d8+50" in result
    assert "Mana dice: 100d10+0" in result
    assert "Damage dice: 2d6+3" in result
    assert "Damage type: slash" in result
    assert "AC: 10d1+0" in result
    assert "Area: Test Area" in result


def test_mstat_requires_vnum(builder_char):
    result = cmd_mstat(builder_char, "")
    assert "Syntax: @mstat <vnum>" in result


def test_mstat_invalid_vnum(builder_char):
    result = cmd_mstat(builder_char, "abc")
    assert "Mobile vnum must be a number" in result


def test_mstat_nonexistent_mobile(builder_char):
    result = cmd_mstat(builder_char, "9999")
    assert "No mobile prototype with vnum 9999" in result


# @goto tests


def test_goto_teleports_to_room(builder_char, test_room):
    # Create another room to teleport to
    target_room = Room(vnum=1002, name="Target Room", area=test_room.area)
    room_registry[1002] = target_room

    result = cmd_goto(builder_char, "1002")

    assert builder_char.room == target_room
    assert "1002" in result
    assert "Target Room" in result

    room_registry.pop(1002, None)


def test_goto_requires_vnum(builder_char):
    result = cmd_goto(builder_char, "")
    assert "Syntax: @goto <room vnum>" in result


def test_goto_invalid_vnum(builder_char):
    result = cmd_goto(builder_char, "abc")
    assert "Room vnum must be a number" in result


def test_goto_nonexistent_room(builder_char):
    result = cmd_goto(builder_char, "9999")
    assert "No room with vnum 9999" in result


def test_goto_shows_from_and_to(builder_char, test_room):
    target_room = Room(vnum=1002, name="Target Room", area=test_room.area)
    room_registry[1002] = target_room

    result = cmd_goto(builder_char, "1002")

    assert "1001" in result  # from vnum
    assert "1002" in result  # to vnum

    room_registry.pop(1002, None)


# @vlist tests


def test_vlist_current_area(builder_char, test_area, test_room, test_object, test_mobile):
    result = cmd_vlist(builder_char, "")

    assert "Area: Test Area" in result
    assert "vnums 1000-1099" in result
    assert "Rooms (1):" in result
    assert "[1001] Test Room" in result
    assert "Mobiles (1):" in result
    assert "[1025] a city guard" in result
    assert "Objects (1):" in result
    assert "[1050] a gleaming sword" in result


def test_vlist_specific_area(builder_char, test_area, test_room):
    result = cmd_vlist(builder_char, "1")

    assert "Area: Test Area" in result
    assert "Rooms (1):" in result


def test_vlist_invalid_vnum(builder_char):
    result = cmd_vlist(builder_char, "abc")
    assert "Area vnum must be a number" in result


def test_vlist_nonexistent_area(builder_char):
    result = cmd_vlist(builder_char, "999")
    assert "No area with vnum 999" in result


def test_vlist_no_current_area(builder_char):
    builder_char.room = None
    result = cmd_vlist(builder_char, "")
    assert "Syntax: @vlist <area vnum>" in result


def test_vlist_limits_display(builder_char, test_area):
    """Test that vlist limits output to 20 items per category."""
    # Create 25 rooms
    for i in range(1000, 1025):
        room = Room(vnum=i, name=f"Room {i}", area=test_area)
        room_registry[i] = room

    result = cmd_vlist(builder_char, "1")

    assert "Rooms (25):" in result
    assert "... and 5 more" in result

    # Cleanup
    for i in range(1000, 1025):
        room_registry.pop(i, None)


def test_vlist_empty_area(builder_char):
    empty_area = Area(vnum=2, name="Empty Area", min_vnum=2000, max_vnum=2099)
    area_registry[2] = empty_area

    result = cmd_vlist(builder_char, "2")

    assert "Area: Empty Area" in result
    assert "vnums 2000-2099" in result
    # Should not show any categories since they're empty

    area_registry.pop(2, None)
