"""INV-025 sweep — equipment commands fire mp_act_trigger on listening NPCs.

ROM contract (``src/act_obj.c:1419, 1435-1612, 1639, 1674``):
``do_wear`` / ``do_wield`` / ``do_hold`` / ``remove_obj`` all call act()
with TO_ROOM and NO MOBtrigger wrap, so per ``src/comm.c:2384`` every
NPC recipient with ``HAS_TRIGGER(TRIG_ACT)`` matching the message must
receive ``mp_act_trigger``.

Locks the contract for the standard wear path (line 1487 "$n wears $p
on $s torso.") and the remove path ("$n stops using $p.").  The other
equipment paths share the same broadcast site so coverage is implicit.
"""

from __future__ import annotations

import pytest

from mud.commands.equipment import do_wear
from mud.commands.obj_manipulation import do_remove
from mud.models.character import Character, character_registry
from mud.models.constants import ItemType, Position, WearFlag, WearLocation
from mud.models.mob import MobIndex
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
    room_registry.pop(9560, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9560, name="Armory", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9560] = room
    return room


def _make_pc(room: Room) -> Character:
    pc = Character(
        name="wearer",
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    pc.inventory = []
    pc.equipment = {}
    pc.alignment = 0
    pc.size = 3
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room, phrase: str, vnum: int = 9561) -> Character:
    from mud.mobprog import Trigger

    listener = Character(
        name=f"watcher_{vnum}",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=vnum, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase=phrase,
            code='mob echo "EQ_SEEN"\n',
            vnum=vnum,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _make_torso_armor(holder: Character) -> Object:
    proto = ObjIndex(
        vnum=9562,
        short_descr="a vest",
        name="vest",
        item_type=int(ItemType.ARMOR),
    )
    proto.weight = 1
    proto.wear_flags = int(WearFlag.TAKE) | int(WearFlag.WEAR_BODY)
    proto.value = [0, 0, 0, 0, 0]
    obj = Object(instance_id=None, prototype=proto)
    obj.wear_flags = int(WearFlag.TAKE) | int(WearFlag.WEAR_BODY)
    obj.extra_flags = 0
    obj.wear_loc = -1
    obj.level = 1
    holder.inventory.append(obj)
    obj.carried_by = holder
    return obj


def test_do_wear_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:1487 act() with no MOBtrigger wrap dispatches TRIG_ACT."""
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "wears")
    obj = _make_torso_armor(pc)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_wear(pc, "vest")
    finally:
        mobprog.mp_act_trigger = original

    _ = obj  # keep reference
    assert fired, (
        "do_wear must dispatch mp_act_trigger on its TO_ROOM broadcast — ROM src/act_obj.c:1487, no MOBtrigger wrap"
    )
    assert "wears" in fired[0][1]


def test_do_remove_fires_act_trigger_on_listening_npc():
    """ROM src/handler.c:remove_obj TO_ROOM ``$n stops using $p.`` no MOBtrigger wrap."""
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "stops")
    obj = _make_torso_armor(pc)
    # Pre-equip
    pc.equipment[int(WearLocation.BODY)] = obj
    obj.worn_by = pc
    obj.wear_loc = int(WearLocation.BODY)
    pc.inventory.remove(obj)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_remove(pc, "vest")
    finally:
        mobprog.mp_act_trigger = original

    assert fired, (
        "do_remove must dispatch mp_act_trigger on its TO_ROOM broadcast — "
        "ROM src/handler.c:remove_obj, no MOBtrigger wrap"
    )
    assert "stops" in fired[0][1]
