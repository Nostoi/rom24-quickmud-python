"""INV-025 sweep - eat/drink act() room lines dispatch TRIG_ACT.

ROM contract (``src/act_obj.c:1238-1241,1317``): ``do_drink`` and
``do_eat`` emit TO_ROOM lines through ``act()`` with no MOBtrigger
suppression. Per ``src/comm.c:2384``, NPC recipients with TRIG_ACT must
receive ``mp_act_trigger`` for those formatted lines.
"""

from __future__ import annotations

import pytest

from mud.commands.consumption import do_drink, do_eat
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import ItemType, Position
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
    room_registry.pop(9580, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9580, name="Pantry", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9580] = room
    return room


def _make_pc(room: Room) -> Character:
    pc = Character(
        name="diner",
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    pc.inventory = []
    pc.pcdata = PCData()
    pc.pcdata.condition = [0, 0, 0, 0]
    pc.condition = pc.pcdata.condition
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room, phrase: str, vnum: int = 9581) -> Character:
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
            code='mob echo "CONSUME_SEEN"\n',
            vnum=vnum,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _make_item(holder: Character, *, item_type: ItemType, name: str, short_descr: str, value: list[int]) -> Object:
    proto = ObjIndex(vnum=9582, name=name, short_descr=short_descr, item_type=int(item_type), value=list(value))
    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = int(item_type)
    obj.value = list(value)
    holder.add_object(obj)
    return obj


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


def test_eat_room_act_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:1317 / src/comm.c:2384 - eat act() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "eats")
    _make_item(pc, item_type=ItemType.FOOD, name="bread", short_descr="a loaf of bread", value=[8, 5, 0, 0, 0])

    fired = _recorded_act_triggers(lambda: do_eat(pc, "bread"))

    assert len(fired) == 1
    assert fired[0][0] == "watcher_9581"
    assert "eats" in fired[0][1]


def test_drink_room_act_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:1238-1241 / src/comm.c:2384 - drink act() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "drinks")
    _make_item(
        pc,
        item_type=ItemType.DRINK_CON,
        name="flask",
        short_descr="a leather flask",
        value=[10, 10, 0, 0, 0],
    )

    fired = _recorded_act_triggers(lambda: do_drink(pc, "flask"))

    assert len(fired) == 1
    assert fired[0][0] == "watcher_9581"
    assert "drinks" in fired[0][1]
