"""Integration tests for ROM-parity give command behavior."""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.mobprog import Trigger
from mud.models.constants import ActFlag, ExtraFlag, ItemType
from mud.models.mob import MobProgram
from mud.models.shop import Shop
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import initialize_world
from mud.world.movement import can_carry_n


@pytest.fixture(scope="module", autouse=True)
def _initialize_world():
    """Initialize world once for give-command integration tests."""
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


def test_give_coins_uses_silver_path_and_broadcasts_room_message(movable_char_factory, test_room_3001):
    """ROM act_obj.c:678-731 treats `coins` as silver and broadcasts room/victim messages."""
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)
    observer = movable_char_factory("Observer", 3001)
    victim.messages = []
    observer.messages = []

    giver.gold = 0
    giver.silver = 9
    victim.gold = 0
    victim.silver = 0

    result = process_command(giver, "give 7 coins receiver")

    victim_text = " ".join(victim.messages).lower()
    observer_text = " ".join(observer.messages).lower()
    assert result.lower() == "you give receiver 7 silver."
    assert giver.silver == 2
    assert victim.silver == 7
    assert "gives you 7 silver" in victim_text
    assert "gives" in observer_text
    assert "some coins" in observer_text


def test_give_object_moves_inventory_to_victim_and_broadcasts(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:828-850 moves the object and emits victim/room messages."""
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)
    observer = movable_char_factory("Observer", 3001)
    victim.messages = []
    observer.messages = []

    apple = object_factory({"vnum": 9201, "name": "apple fruit", "short_descr": "a red apple"})
    giver.add_object(apple)

    result = process_command(giver, "give apple receiver")

    victim_text = " ".join(victim.messages).lower()
    observer_text = " ".join(observer.messages).lower()
    assert result.lower() == "you give a red apple to receiver."
    assert apple not in giver.inventory
    assert apple in victim.inventory
    assert "gives you a red apple" in victim_text
    assert "giver" in observer_text
    assert "gives" in observer_text
    assert "apple" in observer_text


def test_give_item_to_shopkeeper_is_rejected(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:801-806: shopkeepers refuse normal GIVE and tell you to sell it."""
    giver = movable_char_factory("Giver", 3001)
    shopkeeper = movable_char_factory("Shopkeep", 3001)
    shopkeeper.pShop = Shop(keeper=9202)

    gem = object_factory({"vnum": 9202, "name": "gem", "short_descr": "a shiny gem"})
    giver.add_object(gem)

    result = process_command(giver, "give gem shopkeep")

    assert "you'll have to sell that" in result.lower()
    assert gem in giver.inventory
    assert gem not in shopkeeper.inventory


def test_give_equipped_item_requires_removing_it_first(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:794-799: equipped items must be removed before they can be given."""
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)

    armor = object_factory({"vnum": 9203, "name": "armor leather", "short_descr": "a leather jerkin"})
    giver.add_object(armor)
    giver.equip_object(armor, "body")

    result = process_command(giver, "give armor receiver")

    assert result == "You must remove it first."
    assert armor not in giver.inventory
    assert giver.equipment.get("body") is armor
    assert armor not in victim.inventory


def test_give_rejects_item_victim_cannot_see(movable_char_factory, object_factory, test_room_3001):
    """ROM act_obj.c:822-825: if the victim cannot see the object, GIVE is blocked."""
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)

    hidden_gem = object_factory({"vnum": 9204, "name": "gem hidden", "short_descr": "a hidden gem"})
    hidden_gem.extra_flags = int(ExtraFlag.INVIS)
    giver.add_object(hidden_gem)

    result = process_command(giver, "give gem receiver")

    assert result == "Receiver can't see it."
    assert hidden_gem in giver.inventory
    assert hidden_gem not in victim.inventory



def test_give_money_does_not_echo_room_message_back_to_giver(movable_char_factory, test_room_3001):
    """ROM TO_NOTVICT excludes the giver; they should only get the direct char message."""
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)
    observer = movable_char_factory("Observer", 3001)
    giver.messages = []
    victim.messages = []
    observer.messages = []

    giver.silver = 10

    result = process_command(giver, "give 5 silver receiver")

    giver_text = " ".join(giver.messages).lower()
    observer_text = " ".join(observer.messages).lower()
    assert result == "You give Receiver 5 silver."
    assert "some coins" not in giver_text
    assert "some coins" in observer_text


def test_give_object_does_not_echo_room_message_back_to_giver(
    movable_char_factory, object_factory, test_room_3001
):
    """ROM TO_NOTVICT excludes the giver on object GIVE as well."""
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)
    observer = movable_char_factory("Observer", 3001)
    giver.messages = []
    victim.messages = []
    observer.messages = []

    apple = object_factory({"vnum": 9211, "name": "apple fruit", "short_descr": "a red apple"})
    giver.add_object(apple)

    result = process_command(giver, "give apple receiver")

    giver_text = " ".join(giver.messages).lower()
    observer_text = " ".join(observer.messages).lower()
    assert result == "You give a red apple to Receiver."
    assert "gives a red apple to receiver" not in giver_text
    assert "gives a red apple to receiver" in observer_text

def test_give_rejects_when_object_consumes_multiple_carry_slots(
    movable_char_factory, object_factory, test_room_3001
):
    """ROM act_obj.c:811-814 uses get_obj_number(obj), not a flat +1 carry-count check."""
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)

    satchel = object_factory(
        {
            "vnum": 9205,
            "name": "satchel canvas",
            "short_descr": "a canvas satchel",
            "item_type": int(ItemType.CONTAINER),
        }
    )
    apple = object_factory({"vnum": 9206, "name": "apple", "short_descr": "a green apple"})
    bread = object_factory({"vnum": 9207, "name": "bread loaf", "short_descr": "a loaf of bread"})
    satchel.contained_items.extend([apple, bread])
    giver.add_object(satchel)

    victim.carry_number = can_carry_n(victim) - 1

    result = process_command(giver, "give satchel receiver")

    assert result == "Receiver has their hands full."
    assert satchel in giver.inventory
    assert satchel not in victim.inventory



def test_give_rejects_when_object_would_put_victim_over_carry_weight(
    movable_char_factory, object_factory, test_room_3001
):
    """ROM act_obj.c:816-820 rejects GIVE when the victim would exceed carry weight."""
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)

    anvil = object_factory({"vnum": 9209, "name": "anvil iron", "short_descr": "a heavy iron anvil", "weight": 2})
    giver.add_object(anvil)

    from mud.world.movement import can_carry_w

    victim.carry_weight = can_carry_w(victim) - 1

    result = process_command(giver, "give anvil receiver")

    assert result == "Receiver can't carry that much weight."
    assert anvil in giver.inventory
    assert anvil not in victim.inventory


def test_give_numeric_path_rejects_invalid_currency_wording(movable_char_factory, test_room_3001):
    """ROM act_obj.c:689-695 rejects unsupported numeric GIVE currencies with the generic error."""
    giver = movable_char_factory("Giver", 3001)
    movable_char_factory("Receiver", 3001)

    result = process_command(giver, "give 3 copper receiver")

    assert result == "Sorry, you can't do that."


def test_give_numeric_path_requires_target_after_valid_currency(movable_char_factory, test_room_3001):
    """ROM act_obj.c:698-702 asks for a target after a valid numeric money argument."""
    giver = movable_char_factory("Giver", 3001)

    result = process_command(giver, "give 3 gold")

    assert result == "Give what to whom?"


def test_give_all_is_not_supported_by_rom_and_falls_back_to_missing_item(
    movable_char_factory, object_factory, test_room_3001
):
    """ROM do_give has no special `give all` branch; the object lookup simply fails."""
    giver = movable_char_factory("Giver", 3001)
    receiver = movable_char_factory("Receiver", 3001)
    apple = object_factory({"vnum": 9210, "name": "apple fruit", "short_descr": "a red apple"})
    giver.add_object(apple)

    result = process_command(giver, "give all receiver")

    assert result == "You do not have that item."
    assert apple in giver.inventory
    assert apple not in receiver.inventory

def test_give_gold_to_npc_fires_bribe_trigger_with_gold_scaled_to_copper(
    movable_char_factory, test_room_3001, monkeypatch
):
    """ROM act_obj.c:734-735 fires TRIG_BRIBE with gold converted to silver-equivalent units."""
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Collector", 3001)
    victim.is_npc = True
    victim.mob_programs = [MobProgram(trig_type=int(Trigger.BRIBE), trig_phrase="1", vnum=9208, code="")]

    calls: list[tuple[object, object, int]] = []

    def fake_bribe_trigger(mob, ch, amount):
        calls.append((mob, ch, amount))
        return True

    monkeypatch.setattr("mud.mobprog.mp_bribe_trigger", fake_bribe_trigger)

    giver.gold = 5
    victim.gold = 0

    result = process_command(giver, "give 3 gold collector")

    assert result == "You give Collector 3 gold."
    assert giver.gold == 2
    assert victim.gold == 3
    assert calls == [(victim, giver, 300)]


def test_give_silver_to_changer_returns_gold_minus_fee(movable_char_factory, test_room_3001):
    """ROM act_obj.c:737-774 changers convert coins at 95% value and thank the player."""
    giver = movable_char_factory("Giver", 3001)
    changer = movable_char_factory("Changer", 3001)
    giver.messages = []
    changer.messages = []
    changer.is_npc = True
    changer.act = int(ActFlag.IS_NPC | ActFlag.IS_CHANGER)
    changer.gold = 0
    changer.silver = 0

    giver.gold = 0
    giver.silver = 250

    result = process_command(giver, "give 200 silver changer")

    giver_text = " ".join(giver.messages).lower()
    assert result == "You give Changer 200 silver."
    assert giver.gold == 1
    assert giver.silver == 140
    assert changer.gold == 0
    assert changer.silver == 110
    assert "thank you, come again" in giver_text
