"""Integration tests for ``do_remove`` command.

Verifies ROM 2.4b6 parity for the ``remove`` command via the dispatcher.

ROM Parity References:
- src/act_obj.c:do_remove (lines 1740-1763)
- src/handler.c:remove_obj (lines 1372-1392)
- src/handler.c:unequip_char (lines 1804-1877)

Notes:
    ROM ``do_remove`` only handles a single item (``one_argument``).
    The ``remove all`` form is a Python-side derivative-friendly extension
    that we retain. These tests cover both ROM-faithful single-item paths
    and the documented ``all`` extension.

Created: 2026-04-24
"""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.models.character import Character
from mud.models.constants import ExtraFlag, ItemType, WearFlag, WearLocation
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character


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
    """Create a level-10 PC standing in a fresh test room."""
    from mud.models.room import Room

    room = Room(vnum=3001, name="Test Room", description="A test room")
    room_registry[3001] = room

    char = create_test_character("TestChar", room_vnum=3001)
    char.level = 10
    char.is_npc = False
    char.max_hit = 100
    char.hit = 100
    char.max_mana = 100
    char.mana = 100
    char.max_move = 100
    char.move = 100
    char.armor = [100, 100, 100, 100]
    char.perm_stat = [13, 13, 13, 13, 13]
    char.mod_stat = [0, 0, 0, 0, 0]
    if not hasattr(char, "messages"):
        char.messages = []
    return char


@pytest.fixture
def observer_character() -> Character:
    """Second character in the same room to receive TO_ROOM broadcasts."""
    char = create_test_character("Observer", room_vnum=3001)
    char.level = 10
    char.is_npc = False
    if not hasattr(char, "messages"):
        char.messages = []
    return char


def _make_armor(object_factory, vnum: int = 2001):
    return object_factory(
        {
            "vnum": vnum,
            "name": "leather vest",
            "short_descr": "a leather vest",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.TAKE) | int(WearFlag.WEAR_BODY),
            "value": [5, 5, 5, 5],
        }
    )


def test_do_remove_happy_path_emits_both_messages(test_character, observer_character, object_factory):
    """ROM remove_obj: TO_CHAR + TO_ROOM, item returns to inventory, wear_loc reset."""
    char = test_character
    observer = observer_character
    observer.messages = []

    armor = _make_armor(object_factory)
    char.add_object(armor)
    process_command(char, "wear vest")
    assert armor.wear_loc == int(WearLocation.BODY)

    result = process_command(char, "remove vest")

    # TO_CHAR message: ROM "You stop using $p."
    assert result == "You stop using a leather vest."

    # TO_ROOM message: ROM "$n stops using $p."
    assert any("stops using a leather vest" in m for m in observer.messages), (
        f"Observer should see TO_ROOM broadcast, got: {observer.messages}"
    )
    # Actor should NOT have received the TO_ROOM message themselves
    assert not any("TestChar stops using" in m for m in getattr(char, "messages", [])), (
        "Actor must be excluded from their own TO_ROOM broadcast"
    )

    # wear_loc reset to NONE (-1) and item back in inventory
    assert armor.wear_loc == int(WearLocation.NONE)
    assert armor not in char.equipment.values()
    assert armor in char.inventory


def test_do_remove_blocked_by_noremove(test_character, object_factory):
    """ROM: ITEM_NOREMOVE prints 'You can't remove $p.' and item stays equipped."""
    char = test_character

    cursed = object_factory(
        {
            "vnum": 2002,
            "name": "cursed ring",
            "short_descr": "a cursed ring",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.TAKE) | int(WearFlag.WEAR_FINGER),
            "extra_flags": int(ExtraFlag.NOREMOVE),
            "value": [1, 0, 0, 0],
        }
    )
    char.add_object(cursed)
    process_command(char, "wear ring")
    assert cursed.wear_loc == int(WearLocation.FINGER_L) or cursed.wear_loc == int(WearLocation.FINGER_R)
    worn_loc = cursed.wear_loc

    result = process_command(char, "remove ring")

    assert result == "You can't remove a cursed ring."
    # Still equipped
    assert cursed.wear_loc == worn_loc
    assert cursed in char.equipment.values()
    assert cursed not in char.inventory


def test_do_remove_no_args(test_character):
    """ROM: empty argument returns 'Remove what?'."""
    result = process_command(test_character, "remove")
    assert result == "Remove what?"


def test_do_remove_item_not_worn(test_character, object_factory):
    """ROM: get_obj_wear miss returns 'You do not have that item.'"""
    char = test_character

    # Item exists in inventory but is NOT worn
    armor = _make_armor(object_factory, vnum=2003)
    char.add_object(armor)
    assert armor.wear_loc == int(WearLocation.NONE)

    result = process_command(char, "remove vest")
    assert result == "You do not have that item."


def test_do_remove_strips_equipment_bonuses(test_character, object_factory):
    """ROM: unequip_char reverts AC bonus on removal."""
    char = test_character
    initial_ac = list(char.armor)

    armor = _make_armor(object_factory, vnum=2004)
    char.add_object(armor)
    process_command(char, "wear vest")

    # AC improved (lower is better)
    assert char.armor[0] < initial_ac[0]

    process_command(char, "remove vest")

    # AC reverted to original
    assert char.armor == initial_ac


def test_do_remove_all_skips_noremove(test_character, object_factory):
    """Python extension: 'remove all' removes regular equipment, leaves NOREMOVE worn."""
    char = test_character

    armor = _make_armor(object_factory, vnum=2005)
    cursed = object_factory(
        {
            "vnum": 2006,
            "name": "cursed amulet",
            "short_descr": "a cursed amulet",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.TAKE) | int(WearFlag.WEAR_NECK),
            "extra_flags": int(ExtraFlag.NOREMOVE),
            "value": [1, 0, 0, 0],
        }
    )
    char.add_object(armor)
    char.add_object(cursed)
    process_command(char, "wear vest")
    process_command(char, "wear amulet")

    assert armor in char.equipment.values()
    assert cursed in char.equipment.values()

    result = process_command(char, "remove all")

    # Regular item removed, cursed item stays equipped
    assert armor.wear_loc == int(WearLocation.NONE)
    assert armor in char.inventory
    assert armor not in char.equipment.values()

    # NOREMOVE remains worn
    assert cursed in char.equipment.values()
    assert cursed.wear_loc != int(WearLocation.NONE)
    assert cursed not in char.inventory

    # Output mentions removed item
    assert "stop using a leather vest" in result.lower()
