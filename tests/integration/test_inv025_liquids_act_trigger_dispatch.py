"""INV-025 sweep - fill/pour act() room lines dispatch TRIG_ACT.

ROM ``src/act_obj.c:1025,1075,1142,1151,1155`` emits fill/pour visible
lines through unsuppressed ``act()`` calls. Per ``src/comm.c:2384``, matching
NPC recipients must receive TRIG_ACT.
"""

from __future__ import annotations

import pytest

from mud.commands.liquids import do_fill, do_pour
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
    room_registry.pop(9600, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9600, name="Well Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9600] = room
    return room


def _make_pc(room: Room, name: str = "drinker") -> Character:
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
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room, phrase: str, vnum: int = 9601, name: str | None = None) -> Character:
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
    listener.inventory = []
    listener.equipment = {}
    proto = MobIndex(vnum=vnum, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase=phrase,
            code='mob echo "LIQUID_SEEN"\n',
            vnum=vnum,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _make_item(
    *,
    item_type: ItemType,
    name: str,
    short_descr: str,
    value: list[int],
    holder: Character | None = None,
    room: Room | None = None,
) -> Object:
    proto = ObjIndex(vnum=9602, name=name, short_descr=short_descr, item_type=int(item_type), value=list(value))
    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = int(item_type)
    obj.value = list(value)
    if holder is not None:
        holder.add_object(obj)
    if room is not None:
        room.contents.append(obj)
        obj.in_room = room
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


def test_fill_room_act_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:1025 / src/comm.c:2384 - fill act() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "fills")
    _make_item(holder=pc, item_type=ItemType.DRINK_CON, name="flask", short_descr="a tin flask", value=[10, 0, 0, 0, 0])
    _make_item(
        room=room, item_type=ItemType.FOUNTAIN, name="fountain", short_descr="a marble fountain", value=[0, 0, 0, 0, 0]
    )

    fired = _recorded_act_triggers(lambda: do_fill(pc, "flask"))

    assert len(fired) == 1
    assert fired[0][0] == "watcher_9601"
    assert "fills" in fired[0][1]


def test_pour_out_room_act_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:1075 / src/comm.c:2384 - pour out act() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "inverts")
    _make_item(holder=pc, item_type=ItemType.DRINK_CON, name="flask", short_descr="a tin flask", value=[10, 5, 0, 0, 0])

    fired = _recorded_act_triggers(lambda: do_pour(pc, "flask out"))

    assert len(fired) == 1
    assert fired[0][0] == "watcher_9601"
    assert "inverts" in fired[0][1]


def test_pour_object_room_act_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:1142 / src/comm.c:2384 - pour into object act() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room, "pours")
    _make_item(holder=pc, item_type=ItemType.DRINK_CON, name="flask", short_descr="a tin flask", value=[10, 5, 0, 0, 0])
    _make_item(holder=pc, item_type=ItemType.DRINK_CON, name="mug", short_descr="a clay mug", value=[10, 0, 0, 0, 0])

    fired = _recorded_act_triggers(lambda: do_pour(pc, "flask mug"))

    assert len(fired) == 1
    assert fired[0][0] == "watcher_9601"
    assert "pours" in fired[0][1]


def test_pour_character_act_fires_for_victim_and_bystander_not_actor():
    """ROM src/act_obj.c:1151,1155 / src/comm.c:2384 - TO_VICT and TO_NOTVICT both fire."""
    room = _make_room()
    pc = _make_pc(room)
    victim = _make_listener(room, "pours you", vnum=9603, name="target")
    bystander = _make_listener(room, "pours some", vnum=9604, name="bystander")
    _make_item(holder=pc, item_type=ItemType.DRINK_CON, name="flask", short_descr="a tin flask", value=[10, 5, 0, 0, 0])
    held = _make_item(
        holder=victim,
        item_type=ItemType.DRINK_CON,
        name="cup",
        short_descr="a brass cup",
        value=[10, 0, 0, 0, 0],
    )
    victim.inventory.remove(held)
    victim.equipment[WearLocation.HOLD] = held

    fired = _recorded_act_triggers(lambda: do_pour(pc, "flask target"))

    assert fired == [
        (victim.name, "Drinker pours you some water."),
        (bystander.name, "Drinker pours some water for target."),
    ]
