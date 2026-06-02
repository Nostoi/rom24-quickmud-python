"""INV-025 object-command PERS sweep — `act_format(recipient=None)+broadcast_room`.

ROM `act("$n …", TO_ROOM)` renders `$n` through `PERS(ch, looker)` per
recipient (`src/comm.c:act_new`), so an invisible actor renders as "someone"
(capitalized "Someone") to a witness without DETECT_INVIS (INV-027). The object
commands (get/drop/put/quaff/sacrifice/eat) baked the actor name once via
`act_format(..., recipient=None)` (which returns the raw name with no viewer)
and shipped it to every recipient through `broadcast_room` — leaking an
invisible actor's identity. TRIG_ACT was already dispatched at these sites via a
paired `mp_act_trigger_room`; this sweep collapses both into a single
`act_to_room` so the room line is rendered per-recipient.

Each test: invisible actor → witness sees "Someone …"; sighted witness → name.
"""

from __future__ import annotations

import pytest

from mud.commands.consumption import do_eat
from mud.commands.inventory import do_drop, do_get
from mud.commands.obj_manipulation import do_put, do_quaff, do_sacrifice
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import AffectFlag, ItemType, Position, WearFlag
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9590, None)


def _room() -> Room:
    room = Room(vnum=9590, name="Vault", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9590] = room
    return room


def _actor(room: Room, invisible: bool) -> Character:
    ch = Character(
        name="Glark",
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    ch.messages = []
    ch.inventory = []
    ch.pcdata = PCData()
    ch.pcdata.condition = [0, 0, 0, 0]
    ch.condition = ch.pcdata.condition
    room.people.append(ch)
    character_registry.append(ch)
    if invisible:
        ch.add_affect(AffectFlag.INVISIBLE)
    return ch


def _witness(room: Room) -> Character:
    w = Character(name="Witness", is_npc=False, level=18, room=room, position=int(Position.STANDING))
    w.messages = []
    room.people.append(w)
    character_registry.append(w)
    return w


def _obj(*, vnum: int, name: str, short_descr: str, item_type: ItemType, value=None, wear_flags: int = 0) -> Object:
    proto = ObjIndex(
        vnum=vnum,
        name=name,
        short_descr=short_descr,
        item_type=int(item_type),
        value=list(value or [0, 0, 0, 0, 0]),
        wear_flags=wear_flags,
    )
    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = int(item_type)
    obj.value = list(value or [0, 0, 0, 0, 0])
    return obj


def _line(witness: Character) -> str:
    return "\n".join(witness.messages)


def test_get_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    obj = _obj(
        vnum=9591, name="sword", short_descr="a long sword", item_type=ItemType.WEAPON, wear_flags=int(WearFlag.TAKE)
    )
    obj.location = room
    room.contents.append(obj)
    w.messages.clear()

    do_get(ch, "sword")

    assert "Someone gets a long sword." in _line(w), w.messages


def test_get_shows_name_to_sighted_witness():
    room = _room()
    ch = _actor(room, invisible=False)
    w = _witness(room)
    obj = _obj(
        vnum=9591, name="sword", short_descr="a long sword", item_type=ItemType.WEAPON, wear_flags=int(WearFlag.TAKE)
    )
    obj.location = room
    room.contents.append(obj)
    w.messages.clear()

    do_get(ch, "sword")

    assert "Glark gets a long sword." in _line(w), w.messages


def test_drop_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    obj = _obj(vnum=9592, name="shield", short_descr="a steel shield", item_type=ItemType.ARMOR)
    ch.add_object(obj)
    w.messages.clear()

    do_drop(ch, "shield")

    assert "Someone drops a steel shield." in _line(w), w.messages


def test_put_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    container = _obj(
        vnum=9593, name="bag", short_descr="a leather bag", item_type=ItemType.CONTAINER, value=[100, 0, 100, 0, 0]
    )
    ch.add_object(container)
    item = _obj(vnum=9594, name="gem", short_descr="a ruby gem", item_type=ItemType.TREASURE)
    ch.add_object(item)
    w.messages.clear()

    do_put(ch, "gem bag")

    assert "Someone puts a ruby gem in a leather bag." in _line(w), w.messages


def test_quaff_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    potion = _obj(
        vnum=9595, name="potion", short_descr="a blue potion", item_type=ItemType.POTION, value=[10, 0, 0, 0, 0]
    )
    ch.add_object(potion)
    w.messages.clear()

    do_quaff(ch, "potion")

    assert "Someone quaffs a blue potion." in _line(w), w.messages


def test_eat_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    food = _obj(vnum=9596, name="bread", short_descr="a loaf of bread", item_type=ItemType.FOOD, value=[8, 5, 0, 0, 0])
    ch.add_object(food)
    w.messages.clear()

    do_eat(ch, "bread")

    assert "Someone eats a loaf of bread." in _line(w), w.messages


def test_sacrifice_self_decline_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    w.messages.clear()

    do_sacrifice(ch, "Glark")

    # ROM src/act_obj.c:1782 — "$n offers $mself to Mota, who graciously declines."
    assert any(m.startswith("Someone offers") and "Mota" in m for m in w.messages), w.messages
