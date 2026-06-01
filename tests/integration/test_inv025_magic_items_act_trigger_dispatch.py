"""INV-025 sweep - magic item act() room lines dispatch TRIG_ACT.

ROM ``src/act_obj.c:1897,1955,2008,2121`` emits quaff/recite/brandish/zap
room narrations through ``act()`` with no ``MOBtrigger=FALSE`` suppression.
Per ``src/comm.c:2384``, matching NPC recipients must receive TRIG_ACT.
"""

from __future__ import annotations

import pytest

from mud.commands.magic_items import do_brandish, do_recite, do_zap
from mud.commands.obj_manipulation import do_quaff
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import ItemType, Position, WearLocation
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
    room_registry.pop(9590, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9590, name="Laboratory", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9590] = room
    return room


def _make_pc(room: Room, name: str = "caster") -> Character:
    pc = Character(
        name=name,
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    pc.inventory = []
    pc.equipment = {}
    pc.pcdata = PCData()
    pc.pcdata.learned = {"scrolls": 100, "staves": 100, "wands": 100}
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room, phrase: str, vnum: int = 9591, name: str | None = None) -> Character:
    from mud.mobprog import Trigger

    listener = Character(
        name=name or f"watcher_{vnum}",
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
            code='mob echo "MAGIC_ITEM_SEEN"\n',
            vnum=vnum,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _make_item(holder: Character, *, item_type: ItemType, name: str, short_descr: str, value: list) -> Object:
    proto = ObjIndex(vnum=9592, name=name, short_descr=short_descr, item_type=int(item_type), value=list(value))
    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = int(item_type)
    obj.value = list(value)
    obj.level = 1
    holder.add_object(obj)
    return obj


def _hold(char: Character, obj: Object) -> None:
    if obj in char.inventory:
        char.inventory.remove(obj)
    char.equipment[WearLocation.HOLD] = obj


def _recorded_act_triggers(call):
    import mud.mobprog as mobprog

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        call()
    finally:
        mobprog.mp_act_trigger = original
    return fired


def test_quaff_room_act_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:1897 / src/comm.c:2384 - quaff act() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "quaffs")
    _make_item(pc, item_type=ItemType.POTION, name="potion", short_descr="a blue potion", value=[1, 0, 0, 0, 0])

    fired = _recorded_act_triggers(lambda: do_quaff(pc, "potion"))

    assert len(fired) == 1
    assert fired[0][0] == "watcher_9591"
    assert "quaffs" in fired[0][1]


def test_recite_room_act_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:1955 / src/comm.c:2384 - recite act() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "recites")
    _make_item(pc, item_type=ItemType.SCROLL, name="scroll", short_descr="a paper scroll", value=[1, 0, 0, 0, 0])

    fired = _recorded_act_triggers(lambda: do_recite(pc, "scroll"))

    assert len(fired) == 1
    assert fired[0][0] == "watcher_9591"
    assert "recites" in fired[0][1]


def test_brandish_room_act_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:2008 / src/comm.c:2384 - brandish act() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "brandishes")
    staff = _make_item(
        pc,
        item_type=ItemType.STAFF,
        name="staff",
        short_descr="an oak staff",
        value=[1, 0, 3, "armor", 0],
    )
    _hold(pc, staff)

    fired = _recorded_act_triggers(lambda: do_brandish(pc, ""))

    assert len(fired) == 1
    assert fired[0][0] == "watcher_9591"
    assert "brandishes" in fired[0][1]


def test_zap_to_notvict_act_fires_for_bystander_not_npc_victim():
    """ROM src/act_obj.c:2121 / src/comm.c:2384 - zap TO_NOTVICT fires only on recipients."""
    room = _make_room()
    pc = _make_pc(room)
    victim = _make_listener(room, "zaps", vnum=9593, name="target")
    bystander = _make_listener(room, "zaps", vnum=9594, name="bystander")
    wand = _make_item(
        pc,
        item_type=ItemType.WAND,
        name="wand",
        short_descr="a crystal wand",
        value=[1, 0, 3, "armor", 0],
    )
    _hold(pc, wand)

    fired = _recorded_act_triggers(lambda: do_zap(pc, "target"))

    assert len(fired) == 1
    assert fired[0][0] == bystander.name
    assert "zaps" in fired[0][1]
    assert victim.name not in [mob_name for mob_name, _ in fired]
