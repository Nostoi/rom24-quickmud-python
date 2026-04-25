"""Integration tests for ROM-parity drop command behavior."""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.handler import create_money
from mud.models.constants import ExtraFlag, ItemType
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def _initialize_world():
    """Initialize world once for drop-command integration tests."""
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
        room_registry[3001] = Room(vnum=3001, name="Test Room", description="A test room")
    return room_registry[3001]


@pytest.fixture(autouse=True)
def clean_test_state(test_room_3001):
    """Reset room contents and occupants between tests."""
    test_room_3001.contents.clear()
    test_room_3001.people.clear()
    yield
    test_room_3001.contents.clear()
    test_room_3001.people.clear()


def test_drop_all_moves_all_unequipped_inventory_items_to_room(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:619-651: `drop all` drops each visible carried item."""
    player = movable_char_factory("Dropper", 3001)

    apple = object_factory({"vnum": 9101, "name": "apple", "short_descr": "a red apple"})
    bread = object_factory({"vnum": 9102, "name": "bread", "short_descr": "a loaf of bread"})

    player.add_object(apple)
    player.add_object(bread)

    result = process_command(player, "drop all")

    assert apple not in player.inventory
    assert bread not in player.inventory
    assert apple in player.room.contents
    assert bread in player.room.contents
    assert "drop" in result.lower()


def test_drop_all_type_only_drops_matching_inventory_items(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:619-651: `drop all.apple` filters by keyword."""
    player = movable_char_factory("Dropper", 3001)

    apple = object_factory({"vnum": 9103, "name": "apple fruit", "short_descr": "a red apple"})
    green_apple = object_factory({"vnum": 9104, "name": "apple green fruit", "short_descr": "a green apple"})
    bread = object_factory({"vnum": 9105, "name": "bread loaf", "short_descr": "a loaf of bread"})

    player.add_object(apple)
    player.add_object(green_apple)
    player.add_object(bread)

    result = process_command(player, "drop all.apple")

    assert apple not in player.inventory
    assert green_apple not in player.inventory
    assert bread in player.inventory
    assert apple in player.room.contents
    assert green_apple in player.room.contents
    assert bread not in player.room.contents
    assert result.lower().count("you drop") == 2


def test_drop_numeric_gold_consolidates_existing_room_money(movable_char_factory, test_room_3001):
    """ROM act_obj.c:509-589: numeric money drops merge into one room money pile."""
    player = movable_char_factory("Dropper", 3001)
    player.gold = 10
    player.silver = 0

    existing_money = create_money(gold=5, silver=25)
    test_room_3001.add_object(existing_money)

    result = process_command(player, "drop 10 gold")

    room_money = [obj for obj in test_room_3001.contents if getattr(obj, "item_type", None) == int(ItemType.MONEY)]

    assert result == "OK."
    assert player.gold == 0
    assert len(room_money) == 1
    assert room_money[0].value[0] == 25
    assert room_money[0].value[1] == 15


def test_drop_melt_drop_item_dissolves_instead_of_remaining_in_room(
    movable_char_factory, object_factory, test_room_3001
):
    """ROM act_obj.c:610-613: ITEM_MELT_DROP objects dissolve after being dropped."""
    player = movable_char_factory("Dropper", 3001)
    smoke_bomb = object_factory(
        {
            "vnum": 9106,
            "name": "bomb smoke",
            "short_descr": "a smoke bomb",
        }
    )
    smoke_bomb.extra_flags = int(ExtraFlag.MELT_DROP)
    player.add_object(smoke_bomb)

    result = process_command(player, "drop bomb")

    assert smoke_bomb not in player.inventory
    assert smoke_bomb not in test_room_3001.contents
    assert "dissolves into smoke" in result.lower()


def test_drop_melt_drop_item_broadcasts_smoke_message_to_room(
    movable_char_factory, object_factory, test_room_3001
):
    """ROM act_obj.c:612: room observers also see the dissolve message."""
    player = movable_char_factory("Dropper", 3001)
    observer = movable_char_factory("Observer", 3001)
    observer.messages = []

    smoke_bomb = object_factory(
        {
            "vnum": 9107,
            "name": "bomb smoke",
            "short_descr": "a smoke bomb",
        }
    )
    smoke_bomb.extra_flags = int(ExtraFlag.MELT_DROP)
    player.add_object(smoke_bomb)

    process_command(player, "drop bomb")

    room_text = " ".join(observer.messages).lower()
    assert "drops" in room_text
    assert "dissolves into smoke" in room_text


def test_drop_single_object_broadcasts_to_room(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:607: observers see `$n drops $p.` for normal drops."""
    player = movable_char_factory("Dropper", 3001)
    observer = movable_char_factory("Observer", 3001)
    observer.messages = []

    apple = object_factory({"vnum": 9108, "name": "apple fruit", "short_descr": "a red apple"})
    player.add_object(apple)

    result = process_command(player, "drop apple")

    room_text = " ".join(observer.messages).lower()
    assert "you drop a red apple" in result.lower()
    assert "dropper" in room_text
    assert "drops" in room_text
    assert "apple" in room_text


def test_drop_nodrop_item_is_rejected(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:601-604: cursed / no-drop items cannot be dropped."""
    player = movable_char_factory("Dropper", 3001)
    cursed_ring = object_factory(
        {
            "vnum": 9109,
            "name": "ring cursed",
            "short_descr": "a cursed ring",
        }
    )
    cursed_ring.extra_flags = 0x0010
    player.add_object(cursed_ring)

    result = process_command(player, "drop ring")

    assert result == "You can't let go of it."
    assert cursed_ring in player.inventory
    assert cursed_ring not in test_room_3001.contents


def test_drop_numeric_gold_rejects_insufficient_funds(movable_char_factory, test_room_3001):
    """ROM act_obj.c:531-536: dropping more gold than carried is rejected."""
    player = movable_char_factory("Dropper", 3001)
    player.gold = 3
    player.silver = 0

    result = process_command(player, "drop 10 gold")

    assert result == "You don't have that much gold."
    assert player.gold == 3
    assert not [obj for obj in test_room_3001.contents if getattr(obj, "item_type", None) == int(ItemType.MONEY)]


def test_drop_numeric_silver_creates_money_pile(movable_char_factory, test_room_3001):
    """ROM act_obj.c:519-528: numeric silver drops create a silver money object."""
    player = movable_char_factory("Dropper", 3001)
    player.gold = 0
    player.silver = 12

    result = process_command(player, "drop 12 silver")

    room_money = [obj for obj in test_room_3001.contents if getattr(obj, "item_type", None) == int(ItemType.MONEY)]

    assert result == "OK."
    assert player.silver == 0
    assert len(room_money) == 1
    assert room_money[0].value[0] == 12
    assert room_money[0].value[1] == 0


def test_drop_numeric_coins_uses_silver_path(movable_char_factory, test_room_3001):
    """ROM act_obj.c:519-528 treats `coins` like silver for numeric drops."""
    player = movable_char_factory("Dropper", 3001)
    player.gold = 0
    player.silver = 7

    result = process_command(player, "drop 7 coins")

    room_money = [obj for obj in test_room_3001.contents if getattr(obj, "item_type", None) == int(ItemType.MONEY)]

    assert result == "OK."
    assert player.silver == 0
    assert len(room_money) == 1
    assert room_money[0].value[0] == 7
    assert room_money[0].value[1] == 0


def test_drop_numeric_silver_rejects_insufficient_funds(movable_char_factory, test_room_3001):
    """ROM act_obj.c:540-544: dropping more silver than carried is rejected."""
    player = movable_char_factory("Dropper", 3001)
    player.gold = 0
    player.silver = 2

    result = process_command(player, "drop 5 silver")

    assert result == "You don't have that much silver."
    assert player.silver == 2
    assert not [obj for obj in test_room_3001.contents if getattr(obj, "item_type", None) == int(ItemType.MONEY)]


def test_drop_numeric_invalid_money_keyword_is_rejected(movable_char_factory, test_room_3001):
    """ROM act_obj.c:516-523 rejects numeric drops that are not coin keywords."""
    player = movable_char_factory("Dropper", 3001)
    player.gold = 10
    player.silver = 10

    result = process_command(player, "drop 3 apples")

    assert result == "Sorry, you can't do that."
    assert player.gold == 10
    assert player.silver == 10
    assert not test_room_3001.contents


def test_drop_money_broadcasts_some_coins_to_room(movable_char_factory, test_room_3001):
    """ROM act_obj.c:586: numeric money drops emit the room coin-drop message."""
    player = movable_char_factory("Dropper", 3001)
    observer = movable_char_factory("Observer", 3001)
    observer.messages = []
    player.gold = 4

    result = process_command(player, "drop 4 gold")

    room_text = " ".join(observer.messages).lower()
    assert result == "OK."
    assert "dropper" in room_text
    assert "drops some coins" in room_text


def test_drop_all_ignores_equipped_items(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:627-629 only drops WEAR_NONE inventory items."""
    player = movable_char_factory("Dropper", 3001)

    backpack = object_factory({"vnum": 9110, "name": "backpack", "short_descr": "a leather backpack"})
    sword = object_factory({"vnum": 9111, "name": "sword", "short_descr": "a steel sword"})
    sword.wear_loc = 5

    player.add_object(backpack)
    player.add_object(sword)

    result = process_command(player, "drop all")

    assert backpack not in player.inventory
    assert backpack in test_room_3001.contents
    assert sword in player.inventory
    assert sword not in test_room_3001.contents
    assert result.lower().count("you drop") == 1


def test_drop_all_type_without_match_returns_rom_message(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:648-650: unmatched `drop all.type` reports the missing type."""
    player = movable_char_factory("Dropper", 3001)
    bread = object_factory({"vnum": 9112, "name": "bread loaf", "short_descr": "a loaf of bread"})
    player.add_object(bread)

    result = process_command(player, "drop all.apple")

    assert result == "You are not carrying any apple."
    assert bread in player.inventory
    assert bread not in test_room_3001.contents
