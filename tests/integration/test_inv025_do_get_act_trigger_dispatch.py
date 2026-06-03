"""INV-025 sweep — do_get fires mp_act_trigger on listening NPCs.

ROM contract (``src/act_obj.c:151, 158``):

    act ("$n gets $p from $P.", ch, obj, container, TO_ROOM);   /* container */
    act ("$n gets $p.",         ch, obj, container, TO_ROOM);   /* floor */

ROM does NOT wrap these in ``MOBtrigger=FALSE``, so per ``src/comm.c:2384``
every NPC recipient with ``HAS_TRIGGER(TRIG_ACT)`` matching the message
must receive ``mp_act_trigger``.
"""

from __future__ import annotations

import pytest

from mud.commands.inventory import do_get
from mud.models.character import Character, character_registry
from mud.models.constants import Position
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
    room_registry.pop(9530, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9530, name="Plaza", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9530] = room
    return room


def _make_pc(room: Room) -> Character:
    pc = Character(
        name="getter",
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    pc.inventory = []
    pc.equipment = {}
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room) -> Character:
    from mud.mobprog import Trigger

    listener = Character(
        name="watcher",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=9531, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="gets",
            code='mob echo "GET_SEEN"\n',
            vnum=9531,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _make_floor_obj(room: Room) -> Object:
    proto = ObjIndex(vnum=9532, short_descr="a coin", name="coin")
    proto.weight = 1
    proto.wear_flags = 1  # TAKE
    obj = Object(instance_id=None, prototype=proto)
    obj.wear_flags = 1
    obj.extra_flags = 0
    obj.wear_loc = -1
    obj.cost = 0
    room.contents.append(obj)
    obj.in_room = room
    return obj


def test_do_get_floor_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:158 act() with no MOBtrigger wrap dispatches TRIG_ACT."""
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room)
    _make_floor_obj(room)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_get(pc, "coin")
    finally:
        mobprog.mp_act_trigger = original

    assert fired, (
        "do_get must dispatch mp_act_trigger on its TO_ROOM broadcast — ROM src/act_obj.c:158, no MOBtrigger wrap"
    )
    assert fired[0][0] == "watcher"
    assert "gets" in fired[0][1]
