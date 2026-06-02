"""INV-025 equipment PERS sweep — baked-name f-strings in mud/commands/equipment.py.

ROM `do_wear`/`do_wield`/`do_hold`/`remove_obj` emit their TO_ROOM lines through
`act("$n …", TO_ROOM)` (`src/act_obj.c:1389/1410/1419/1639/1674`, 1435-1612),
so `$n` masks an invisible actor to "Someone" per recipient (INV-027) and `$s`
renders the actor's gendered possessive. Python baked `f"{ch.name} …"` (and the
wear-slot path baked the name via `act_format(recipient=None)`) into
`broadcast_room`, leaking an invisible actor's name; the hold line also used a
literal "their hand" instead of ROM's `$s hand`. Converted every site to
`act_to_room`.

Each test: invisible actor → witness sees "Someone …"; the hold line also checks
the `$s` gendered possessive.
"""

from __future__ import annotations

import pytest

from mud.commands.equipment import do_wear, do_wield
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, ItemType, Position, Sex, WearFlag
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
    room_registry.pop(9570, None)


def _room() -> Room:
    room = Room(vnum=9570, name="Armory", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9570] = room
    return room


def _actor(room: Room, *, invisible: bool, sex: Sex = Sex.MALE, level: int = 20) -> Character:
    ch = Character(
        name="Glark",
        is_npc=False,
        level=level,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    ch.messages = []
    ch.inventory = []
    ch.equipment = {}
    ch.alignment = 0
    ch.size = 3
    ch.sex = sex
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


def _obj(
    holder: Character, *, vnum: int, name: str, short_descr: str, item_type: ItemType, wear_flags: int, level: int = 1
) -> Object:
    proto = ObjIndex(vnum=vnum, name=name, short_descr=short_descr, item_type=int(item_type))
    proto.weight = 1
    proto.wear_flags = wear_flags
    proto.value = [0, 0, 0, 0, 0]
    proto.level = level
    obj = Object(instance_id=None, prototype=proto)
    obj.wear_flags = wear_flags
    obj.extra_flags = 0
    obj.wear_loc = -1
    obj.level = level
    holder.inventory.append(obj)
    obj.carried_by = holder
    return obj


def _line(witness: Character) -> str:
    return "\n".join(witness.messages)


def test_wear_slot_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    _obj(
        ch,
        vnum=9571,
        name="vest",
        short_descr="a leather vest",
        item_type=ItemType.ARMOR,
        wear_flags=int(WearFlag.TAKE) | int(WearFlag.WEAR_BODY),
    )
    w.messages.clear()

    do_wear(ch, "vest")

    # ROM act_obj.c:1487 "$n wears $p on $s torso." — invisible actor → "Someone".
    assert "Someone wears a leather vest on his torso." in _line(w), w.messages


def test_wield_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    _obj(
        ch,
        vnum=9572,
        name="sword",
        short_descr="a long sword",
        item_type=ItemType.WEAPON,
        wear_flags=int(WearFlag.TAKE) | int(WearFlag.WIELD),
    )
    w.messages.clear()

    do_wield(ch, "sword")

    # ROM act_obj.c:1639 "$n wields $p."
    assert "Someone wields a long sword." in _line(w), w.messages


def test_hold_masks_invisible_actor_and_uses_gendered_possessive():
    room = _room()
    ch = _actor(room, invisible=True, sex=Sex.FEMALE)
    w = _witness(room)
    _obj(
        ch,
        vnum=9573,
        name="wand",
        short_descr="a glowing wand",
        item_type=ItemType.TREASURE,
        wear_flags=int(WearFlag.TAKE) | int(WearFlag.HOLD),
    )
    w.messages.clear()

    do_wear(ch, "wand")

    # ROM act_obj.c:1674 "$n holds $p in $s hand." — invisible → "Someone", $s=her.
    assert "Someone holds a glowing wand in her hand." in _line(w), w.messages


def test_light_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    _obj(
        ch,
        vnum=9574,
        name="torch",
        short_descr="a flaming torch",
        item_type=ItemType.LIGHT,
        wear_flags=int(WearFlag.TAKE),
    )
    w.messages.clear()

    do_wear(ch, "torch")

    # ROM act_obj.c:1419 "$n lights $p and holds it."
    assert "Someone lights a flaming torch and holds it." in _line(w), w.messages


def test_level_fail_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True, level=5)
    w = _witness(room)
    _obj(
        ch,
        vnum=9575,
        name="plate",
        short_descr="a mithril breastplate",
        item_type=ItemType.ARMOR,
        wear_flags=int(WearFlag.TAKE) | int(WearFlag.WEAR_BODY),
        level=50,
    )
    w.messages.clear()

    do_wear(ch, "plate")

    # ROM act_obj.c:1410 "$n tries to use $p, but is too inexperienced."
    assert "Someone tries to use a mithril breastplate, but is too inexperienced." in _line(w), w.messages
