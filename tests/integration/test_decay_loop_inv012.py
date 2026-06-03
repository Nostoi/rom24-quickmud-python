"""End-to-end decay loop coverage — INV-012 / INV-013 / INV-014.

ROM ``src/update.c:obj_update`` walks ``object_list``, decrements
timers, and on expiry calls ``src/handler.c:extract_obj`` which
recursively extracts contents and removes the obj from
``object_list``. Three contracts intersect here:

- INV-014: every live obj is on ``object_registry``; extract removes.
- INV-013: extracting a carried obj must release the carrier field.
- INV-011: extracting a carried obj must update ``carry_weight`` and
  ``carry_number``.

The pre-existing ``test_obj_update_decays_corpse`` and
``test_obj_update_spills_floating_container`` cover the room-carried
and floating-container cases. These tests fill the remaining
end-to-end gaps for the INV-012 newly-live registry: carried-obj
decay and recursive nested-container decay.
"""

from __future__ import annotations

import pytest

from mud.game_loop import obj_update
from mud.models.character import Character, character_registry
from mud.models.constants import LEVEL_IMMORTAL, ItemType
from mud.models.obj import ObjIndex, object_registry
from mud.models.object import create_object
from mud.models.room import Room
from mud.registry import room_registry
from mud.skills.handlers import locate_object

_ROOM_VNUM = 9601


@pytest.fixture
def decay_room() -> Room:
    room = room_registry.get(_ROOM_VNUM)
    if room is None:
        room = Room(vnum=_ROOM_VNUM, name="Decay Test Room")
        room_registry[_ROOM_VNUM] = room
    room.contents.clear()
    room.people.clear()
    return room


def test_decay_of_carried_obj_updates_carry_counters_and_registry(
    decay_room: Room,
) -> None:
    """A potion in a character's inventory whose timer expires must:
    extract from ``object_registry`` (INV-014), clear the carrier
    field (INV-013), and decrement ``carry_weight`` / ``carry_number``
    (INV-011). End-to-end check across all three invariants.
    """

    carrier = Character(name="Drinker", is_npc=False)
    carrier.level = 30
    decay_room.add_character(carrier)
    character_registry.append(carrier)

    proto = ObjIndex(
        vnum=9602,
        name="potion",
        short_descr="a potion of healing",
        item_type=int(ItemType.POTION),
        weight=2,
        value=[0, 0, 0, 0, 0],
    )
    potion = create_object(proto)
    potion.timer = 1
    potion.item_type = int(ItemType.POTION)
    carrier.add_object(potion)

    assert potion in object_registry
    assert potion.carried_by is carrier
    initial_weight = carrier.carry_weight
    initial_number = carrier.carry_number
    assert initial_weight >= 2  # potion weight contributed
    assert initial_number >= 1

    obj_update()

    assert potion not in object_registry, (
        "INV-014: decayed obj must be removed from object_registry by _extract_obj (mud/game_loop.py)."
    )
    assert potion not in carrier.inventory
    assert carrier.carry_weight < initial_weight, "INV-011: decay of carried obj must decrement carry_weight."
    assert carrier.carry_number < initial_number, "INV-011: decay of carried obj must decrement carry_number."


def test_npc_corpse_decay_recursively_extracts_contents(
    decay_room: Room,
) -> None:
    """ROM ``extract_obj`` recurses through container contents
    (``src/handler.c:2063-2067``). NPC corpses are NOT in the spill
    branch of ``obj_update`` — when the corpse timer expires, every
    item inside is destroyed with it. INV-014: all three objects
    must leave ``object_registry``.

    Contrast with float-container decay, where contents spill to the
    room and survive (covered by
    ``tests/test_game_loop.py::test_obj_update_spills_floating_container``).
    """

    corpse_proto = ObjIndex(
        vnum=9610,
        name="orc corpse",
        short_descr="the corpse of an orc",
        item_type=int(ItemType.CORPSE_NPC),
    )
    corpse = create_object(corpse_proto)
    corpse.item_type = int(ItemType.CORPSE_NPC)
    corpse.timer = 1

    pouch_proto = ObjIndex(
        vnum=9611,
        name="pouch",
        short_descr="a leather pouch",
        item_type=int(ItemType.CONTAINER),
    )
    pouch = create_object(pouch_proto)
    pouch.item_type = int(ItemType.CONTAINER)

    gem_proto = ObjIndex(
        vnum=9612,
        name="ruby",
        short_descr="a ruby",
        item_type=int(ItemType.GEM),
    )
    gem = create_object(gem_proto)
    gem.item_type = int(ItemType.GEM)

    pouch.contained_items.append(gem)
    gem.in_obj = pouch
    corpse.contained_items.append(pouch)
    pouch.in_obj = corpse
    decay_room.add_object(corpse)

    assert all(o in object_registry for o in (corpse, pouch, gem))

    obj_update()

    assert corpse not in object_registry, "INV-014: decayed corpse must be removed from registry."
    assert pouch not in object_registry, (
        "ROM extract_obj recurses through contents; INV-014 contract "
        "requires the pouch nested inside the corpse to leave the "
        "registry too."
    )
    assert gem not in object_registry, (
        "Deeply nested items (gem in pouch in corpse) must also be extracted by the recursion."
    )


def test_decayed_obj_invisible_to_locate(decay_room: Room) -> None:
    """Downstream INV-014 consequence: after decay, ``locate object``
    can no longer find the obj (it walks ``object_registry``).
    """

    seer = Character(
        name="Seer",
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        is_npc=False,
    )
    character_registry.append(seer)

    proto = ObjIndex(
        vnum=9620,
        name="ephemeral wisp",
        short_descr="an ephemeral wisp",
        item_type=int(ItemType.FOOD),
    )
    wisp = create_object(proto)
    wisp.item_type = int(ItemType.FOOD)
    wisp.timer = 1
    decay_room.add_object(wisp)

    # Pre-decay: locate finds it.
    seer.messages.clear()
    assert locate_object(seer, "wisp") is True

    obj_update()

    # Post-decay: locate misses it.
    seer.messages.clear()
    assert locate_object(seer, "wisp") is False
    assert seer.messages[-1] == "Nothing like that in heaven or earth."

    character_registry.remove(seer)
