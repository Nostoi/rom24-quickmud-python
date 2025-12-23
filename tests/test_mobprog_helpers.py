"""
Test mobprog helper functions for ROM parity.

ROM Reference: src/mob_prog.c
"""

from __future__ import annotations

import pytest

from mud.mobprog import count_people_room, get_mob_vnum_room, get_obj_vnum_room, has_item, keyword_lookup


@pytest.fixture(scope="module", autouse=True)
def load_world():
    """Load Midgaard area for room 3001."""
    from mud.world.world_state import initialize_world

    initialize_world(use_json=True)


@pytest.fixture(autouse=True)
def clear_room_3001():
    """Clear room 3001 before each test for isolation."""
    from mud.registry import room_registry

    room = room_registry.get(3001)
    if room:
        room.people.clear()
        room.contents.clear()
    yield


def test_count_people_room_all(movable_char_factory, movable_mob_factory):
    """Test count_people_room with flag=0 (all characters)."""
    mob = movable_mob_factory(3000, 3001)
    char1 = movable_char_factory("TestChar1", 3001)
    char2 = movable_char_factory("TestChar2", 3001)
    mob2 = movable_mob_factory(3001, 3001)

    # Should count all 3 others (excluding mob itself)
    assert count_people_room(mob, 0) == 3


def test_count_people_room_players_only(movable_char_factory, movable_mob_factory):
    """Test count_people_room with flag=1 (players only)."""
    mob = movable_mob_factory(3000, 3001)
    char1 = movable_char_factory("Player1", 3001)
    char2 = movable_char_factory("Player2", 3001)
    mob2 = movable_mob_factory(3001, 3001)

    # Should count only 2 players
    assert count_people_room(mob, 1) == 2


def test_count_people_room_npcs_only(movable_char_factory, movable_mob_factory):
    """Test count_people_room with flag=2 (NPCs only)."""
    mob = movable_mob_factory(3000, 3001)
    char1 = movable_char_factory("Player1", 3001)
    mob2 = movable_mob_factory(3001, 3001)
    mob3 = movable_mob_factory(3002, 3001)

    # Should count 2 NPCs (excluding mob itself)
    assert count_people_room(mob, 2) == 2


def test_count_people_room_same_vnum(movable_mob_factory):
    """Test count_people_room with flag=3 (NPCs with same vnum)."""
    mob = movable_mob_factory(3000, 3001)
    mob2 = movable_mob_factory(3000, 3001)  # Same vnum
    mob3 = movable_mob_factory(3000, 3001)  # Same vnum
    mob4 = movable_mob_factory(3001, 3001)  # Different vnum

    # Should count only 2 clones (same vnum, excluding mob itself)
    assert count_people_room(mob, 3) == 2


def test_count_people_room_group_members(movable_char_factory):
    """Test count_people_room with flag=4 (group members)."""
    leader = movable_char_factory("Leader", 3001)
    follower1 = movable_char_factory("Follower1", 3001)
    follower2 = movable_char_factory("Follower2", 3001)
    stranger = movable_char_factory("Stranger", 3001)

    # Set up group
    follower1.leader = leader
    follower2.leader = leader

    # Leader should count 2 followers
    assert count_people_room(leader, 4) == 2


def test_count_people_room_empty_room(movable_mob_factory):
    """Test count_people_room with only the mob in room."""
    mob = movable_mob_factory(3000, 3001)

    # Should count 0 (mob doesn't count itself)
    assert count_people_room(mob, 0) == 0


def test_keyword_lookup_found():
    """Test keyword_lookup finds keyword in table."""
    table = ["north", "south", "east", "west", "\n"]

    assert keyword_lookup(table, "north") == 0
    assert keyword_lookup(table, "south") == 1
    assert keyword_lookup(table, "east") == 2
    assert keyword_lookup(table, "west") == 3


def test_keyword_lookup_case_insensitive():
    """Test keyword_lookup is case-insensitive."""
    table = ["NorTH", "SouTH", "\n"]

    assert keyword_lookup(table, "north") == 0
    assert keyword_lookup(table, "NORTH") == 0
    assert keyword_lookup(table, "NoRtH") == 0


def test_keyword_lookup_not_found():
    """Test keyword_lookup returns -1 when not found."""
    table = ["north", "south", "\n"]

    assert keyword_lookup(table, "invalid") == -1
    assert keyword_lookup(table, "") == -1


def test_keyword_lookup_empty_table():
    """Test keyword_lookup with empty table."""
    assert keyword_lookup([], "anything") == -1
    assert keyword_lookup(["\n"], "anything") == -1


def test_keyword_lookup_stops_at_newline():
    """Test keyword_lookup stops at newline terminator."""
    table = ["valid1", "valid2", "\n", "invalid"]

    assert keyword_lookup(table, "valid1") == 0
    assert keyword_lookup(table, "valid2") == 1
    assert keyword_lookup(table, "invalid") == -1  # After terminator


def test_has_item_by_vnum(movable_char_factory, object_factory):
    """Test has_item finds item by vnum."""
    char = movable_char_factory("TestChar", 3001)
    obj = object_factory({"vnum": 1234, "short_descr": "a test object"})
    char.add_object(obj)

    assert has_item(char, vnum=1234) is True
    assert has_item(char, vnum=9999) is False


def test_has_item_by_type(movable_char_factory, object_factory):
    """Test has_item finds item by item_type."""
    from mud.models.constants import ItemType

    char = movable_char_factory("TestChar", 3001)
    sword = object_factory({"vnum": 1234, "item_type": int(ItemType.WEAPON)})
    char.add_object(sword)

    assert has_item(char, item_type=int(ItemType.WEAPON)) is True
    assert has_item(char, item_type=int(ItemType.ARMOR)) is False


def test_has_item_requires_worn(movable_char_factory, object_factory):
    """Test has_item with require_worn flag."""
    from mud.models.constants import ItemType

    char = movable_char_factory("TestChar", 3001)
    sword = object_factory({"vnum": 1234, "item_type": int(ItemType.WEAPON)})
    char.add_object(sword)

    assert has_item(char, vnum=1234, require_worn=False) is True
    assert has_item(char, vnum=1234, require_worn=True) is False

    char.equipment["wield"] = sword

    assert has_item(char, vnum=1234, require_worn=True) is True


def test_has_item_both_vnum_and_type(movable_char_factory, object_factory):
    """Test has_item matches both vnum AND item_type when both specified."""
    from mud.models.constants import ItemType

    char = movable_char_factory("TestChar", 3001)
    sword = object_factory({"vnum": 1234, "item_type": int(ItemType.WEAPON)})
    char.add_object(sword)

    # Both match
    assert has_item(char, vnum=1234, item_type=int(ItemType.WEAPON)) is True

    # Vnum matches but type doesn't
    assert has_item(char, vnum=1234, item_type=int(ItemType.ARMOR)) is False

    # Type matches but vnum doesn't
    assert has_item(char, vnum=9999, item_type=int(ItemType.WEAPON)) is False


def test_get_mob_vnum_room_found(movable_char_factory, movable_mob_factory):
    """Test get_mob_vnum_room finds mob by vnum."""
    char = movable_char_factory("TestChar", 3001)
    mob1 = movable_mob_factory(3000, 3001)
    mob2 = movable_mob_factory(3001, 3001)

    assert get_mob_vnum_room(char, 3000) is True
    assert get_mob_vnum_room(char, 3001) is True
    assert get_mob_vnum_room(char, 9999) is False


def test_get_mob_vnum_room_ignores_players(movable_char_factory):
    """Test get_mob_vnum_room ignores player characters."""
    char1 = movable_char_factory("TestChar1", 3001)
    char2 = movable_char_factory("TestChar2", 3001)

    # Players don't have vnums, should not be found
    assert get_mob_vnum_room(char1, 0) is False


def test_get_mob_vnum_room_no_room(movable_char_factory):
    """Test get_mob_vnum_room when character not in room."""
    from mud.models.character import Character

    char = Character(name="Homeless")
    assert char.room is None
    assert get_mob_vnum_room(char, 3000) is False


def test_get_obj_vnum_room_found(movable_char_factory, place_object_factory):
    """Test get_obj_vnum_room finds object by vnum."""
    char = movable_char_factory("TestChar", 3001)
    place_object_factory(room_vnum=3001, proto_kwargs={"vnum": 1234})
    place_object_factory(room_vnum=3001, proto_kwargs={"vnum": 5678})

    assert get_obj_vnum_room(char, 1234) is True
    assert get_obj_vnum_room(char, 5678) is True
    assert get_obj_vnum_room(char, 9999) is False


def test_get_obj_vnum_room_ignores_inventory(movable_char_factory, object_factory):
    """Test get_obj_vnum_room only checks room contents, not inventory."""
    char = movable_char_factory("TestChar", 3001)
    obj = object_factory({"vnum": 1234})
    char.add_object(obj)  # In inventory, not room

    # Should not find it (only checks room.contents)
    assert get_obj_vnum_room(char, 1234) is False


def test_get_obj_vnum_room_no_room(movable_char_factory):
    """Test get_obj_vnum_room when character not in room."""
    from mud.models.character import Character

    char = Character(name="Homeless")
    assert char.room is None
    assert get_obj_vnum_room(char, 1234) is False
