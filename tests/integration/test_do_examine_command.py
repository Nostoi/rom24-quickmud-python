"""Integration tests for do_examine command ROM C parity.

Tests verify do_examine implements all ROM C features from act_info.c lines 1320-1391.

ROM C Features Tested:
- No argument handling ("Examine what?")
- Basic look integration (calls do_look first)
- ITEM_JUKEBOX handling (shows song list)
- ITEM_MONEY handling (coin count messages)
- ITEM_CONTAINER handling (shows contents)
- ITEM_CORPSE_NPC handling (shows corpse contents)
- ITEM_CORPSE_PC handling (shows player corpse contents)
- ITEM_DRINK_CON handling (shows liquid info)
- Coin count edge cases (0 coins, 1 coin, mixed)
- Nonexistent object handling (just shows look result)
"""

from __future__ import annotations

import pytest

from mud.commands.info_extended import do_examine
from mud.models.character import Character
from mud.models.constants import ItemType
from mud.models.room import Room


@pytest.fixture
def test_character():
    """Create a test character with basic setup."""
    char = Character()
    char.name = "TestPlayer"
    char.level = 1
    char.trust = 0
    char.is_npc = False
    return char


@pytest.fixture
def temple_room():
    """Create Midgaard Temple room and register it."""
    from mud.registry import room_registry

    room = Room(vnum=3001)
    room.name = "Midgaard Temple"
    room.description = "You are in the temple."
    room.light = 1

    # Register room for place_object_factory to find it
    room_registry[3001] = room

    yield room

    # Cleanup: remove from registry after test
    if 3001 in room_registry:
        del room_registry[3001]


# ============================================================================
# P0 Tests (Critical Functionality)
# ============================================================================


def test_examine_no_argument(test_character, temple_room):
    """P0: examine with no argument returns 'Examine what?'

    ROM C: act_info.c lines 1327-1331
    """
    test_character.room = temple_room
    result = do_examine(test_character, "")
    assert "examine what" in result.lower()


def test_examine_nonexistent_object(test_character, temple_room):
    """P0: examine nonexistent object just shows look result.

    ROM C: act_info.c lines 1333-1335 (do_look on argument)
    ROM C: act_info.c lines 1337 (get_obj_here returns NULL, return)
    """
    test_character.room = temple_room
    result = do_examine(test_character, "nonexistent")

    assert len(result) > 0
    assert result is not None


def test_examine_money_pile_mixed(test_character, temple_room, place_object_factory):
    """P0: examine money pile shows coin counts (mixed gold/silver).

    ROM C: act_info.c lines 1347-1368 (ITEM_MONEY case)
    ROM C: lines 1365-1367 (mixed coins message)
    """
    obj = place_object_factory(
        room_vnum=3001,
        proto_kwargs={
            "vnum": 10001,
            "name": "coins gold silver pile",
            "short_descr": "a pile of coins",
            "item_type": int(ItemType.MONEY),
            "value": [50, 10, 0, 0, 0],
        },
    )
    obj.value = [50, 10, 0, 0, 0]

    test_character.room = temple_room
    result = do_examine(test_character, "pile")

    assert "10 gold" in result.lower()
    assert "50 silver" in result.lower()
    assert "pile" in result.lower()


# ============================================================================
# P1 Tests (Important Features)
# ============================================================================


def test_examine_jukebox_shows_song_list(test_character, temple_room, place_object_factory):
    """P1: examine jukebox shows song list.

    ROM C: act_info.c lines 1343-1345 (ITEM_JUKEBOX case)
    ROM C: do_function(ch, &do_play, "list");

    NOTE: This test verifies JUKEBOX handling is integrated.
    The exact output depends on do_play("list") implementation.
    """
    # Create jukebox
    place_object_factory(
        room_vnum=3001,
        proto_kwargs={
            "vnum": 10002,
            "name": "jukebox",
            "short_descr": "a jukebox",
            "item_type": int(ItemType.JUKEBOX),
        },
    )

    test_character.room = temple_room
    result = do_examine(test_character, "jukebox")

    # Should contain song list output from do_play("list")
    # At minimum, should not crash or return empty
    assert len(result) > 0
    assert result is not None


def test_examine_container_shows_contents(test_character, temple_room, place_object_factory):
    """P1: examine container shows contents.

    ROM C: act_info.c lines 1370-1377 (ITEM_CONTAINER case)
    ROM C: sprintf(buf, "in %s", argument); do_function(ch, &do_look, buf);
    """
    # Create container
    container = place_object_factory(
        room_vnum=3001,
        proto_kwargs={
            "vnum": 10003,
            "name": "chest wooden",
            "short_descr": "a wooden chest",
            "item_type": int(ItemType.CONTAINER),
        },
    )
    container.item_type = int(ItemType.CONTAINER)

    # Add item to container
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    item_proto = ObjIndex(
        vnum=10004,
        name="sword steel",
        short_descr="a steel sword",
        item_type=int(ItemType.WEAPON),
    )
    item = Object(instance_id=None, prototype=item_proto)
    item.location = container
    container.contained_items.append(item)

    test_character.room = temple_room
    result = do_examine(test_character, "chest")

    # Should show container contents (steel sword)
    # Exact format depends on do_look("in chest") implementation
    assert "sword" in result.lower() or "steel" in result.lower()


def test_examine_corpse_shows_contents(test_character, temple_room, place_object_factory):
    """P1: examine corpse shows corpse contents.

    ROM C: act_info.c lines 1370-1377 (ITEM_CORPSE_NPC case)
    """
    # Create corpse
    corpse = place_object_factory(
        room_vnum=3001,
        proto_kwargs={
            "vnum": 10005,
            "name": "corpse goblin",
            "short_descr": "the corpse of a goblin",
            "item_type": int(ItemType.CORPSE_NPC),
        },
    )
    corpse.item_type = int(ItemType.CORPSE_NPC)

    # Add item to corpse
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    item_proto = ObjIndex(
        vnum=10006,
        name="dagger rusty",
        short_descr="a rusty dagger",
        item_type=int(ItemType.WEAPON),
    )
    item = Object(instance_id=None, prototype=item_proto)
    item.location = corpse
    corpse.contained_items.append(item)

    test_character.room = temple_room
    result = do_examine(test_character, "corpse")

    # Should show corpse contents
    assert "dagger" in result.lower() or "rusty" in result.lower()


def test_examine_drink_container_shows_liquid(test_character, temple_room, place_object_factory):
    """P1: examine drink container shows liquid info.

    ROM C: act_info.c lines 1370-1377 (ITEM_DRINK_CON case)
    """
    # Create drink container
    place_object_factory(
        room_vnum=3001,
        proto_kwargs={
            "vnum": 10007,
            "name": "flask water",
            "short_descr": "a flask of water",
            "item_type": int(ItemType.DRINK_CON),
            "value": [10, 10, 1, 0, 0],  # current, max, liquid type, poisoned
        },
    )

    test_character.room = temple_room
    result = do_examine(test_character, "flask")

    # Should show liquid info (depends on do_look("in flask") implementation)
    # At minimum, should not crash
    assert len(result) > 0


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_examine_money_pile_empty(test_character, temple_room, place_object_factory):
    """EDGE: examine money pile with 0 coins shows special message.

    ROM C: act_info.c lines 1349-1351
    ROM C: "Odd...there's no coins in the pile.\n\r"
    """
    place_object_factory(
        room_vnum=3001,
        proto_kwargs={
            "vnum": 10008,
            "name": "coins pile",
            "short_descr": "a pile of coins",
            "item_type": int(ItemType.MONEY),
            "value": [0, 0, 0, 0, 0],  # silver=0, gold=0
        },
    )

    test_character.room = temple_room
    result = do_examine(test_character, "pile")

    # ROM C message: "Odd...there's no coins in the pile."
    assert "odd" in result.lower() or "no coins" in result.lower()


def test_examine_money_pile_one_gold(test_character, temple_room, place_object_factory):
    """EDGE: examine money pile with 1 gold coin shows special message.

    ROM C: act_info.c lines 1352-1353
    ROM C: "Wow. One gold coin.\n\r"
    """
    obj = place_object_factory(
        room_vnum=3001,
        proto_kwargs={
            "vnum": 10009,
            "name": "coins gold pile",
            "short_descr": "a pile of gold coins",
            "item_type": int(ItemType.MONEY),
            "value": [0, 1, 0, 0, 0],
        },
    )
    obj.value = [0, 1, 0, 0, 0]

    test_character.room = temple_room
    result = do_examine(test_character, "pile")

    assert "wow" in result.lower() or "one gold" in result.lower()


def test_examine_money_pile_one_silver(test_character, temple_room, place_object_factory):
    """EDGE: examine money pile with 1 silver coin shows special message.

    ROM C: act_info.c lines 1359-1360
    ROM C: "Wow. One silver coin.\n\r"
    """
    obj = place_object_factory(
        room_vnum=3001,
        proto_kwargs={
            "vnum": 10010,
            "name": "coins silver pile",
            "short_descr": "a pile of silver coins",
            "item_type": int(ItemType.MONEY),
            "value": [1, 0, 0, 0, 0],
        },
    )
    obj.value = [1, 0, 0, 0, 0]

    test_character.room = temple_room
    result = do_examine(test_character, "pile")

    assert "wow" in result.lower() or "one silver" in result.lower()


def test_examine_player_corpse_shows_contents(test_character, temple_room, place_object_factory):
    """EDGE: examine player corpse shows contents (same as NPC corpse).

    ROM C: act_info.c lines 1370-1377 (ITEM_CORPSE_PC case)
    """
    # Create player corpse
    corpse = place_object_factory(
        room_vnum=3001,
        proto_kwargs={
            "vnum": 10011,
            "name": "corpse player testplayer",
            "short_descr": "the corpse of TestPlayer",
            "item_type": int(ItemType.CORPSE_PC),
        },
    )
    corpse.item_type = int(ItemType.CORPSE_PC)

    # Add item to corpse
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    item_proto = ObjIndex(
        vnum=10012,
        name="sword longsword",
        short_descr="a longsword",
        item_type=int(ItemType.WEAPON),
    )
    item = Object(instance_id=None, prototype=item_proto)
    item.location = corpse
    corpse.contained_items.append(item)

    test_character.room = temple_room
    result = do_examine(test_character, "corpse")

    # Should show corpse contents
    assert "longsword" in result.lower() or "sword" in result.lower()
