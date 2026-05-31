"""INV-025 sweep — do_open fires mp_act_trigger on listening NPCs.

ROM contract (``src/act_move.c:436``):

    act ("$n opens the $d.", ch, NULL, pexit->keyword, TO_ROOM);

ROM does NOT wrap this in ``MOBtrigger=FALSE``, so per ``src/comm.c:2384``
every NPC recipient of the act() line with ``HAS_TRIGGER(TRIG_ACT)`` matching
the message must receive ``mp_act_trigger``.
"""

from __future__ import annotations

import pytest

from mud.commands.doors import do_open
from mud.models.character import Character, character_registry
from mud.models.constants import EX_CLOSED, EX_ISDOOR, Direction, Position
from mud.models.mob import MobIndex
from mud.models.room import Exit, Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9590, None)
    room_registry.pop(9591, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_rooms() -> tuple[Room, Room]:
    room = Room(vnum=9590, name="Entry", description="", room_flags=0, sector_type=0)
    other = Room(vnum=9591, name="Hall", description="", room_flags=0, sector_type=0)
    for candidate in (room, other):
        candidate.people = []
        candidate.contents = []
        candidate.exits = [None] * 6
        room_registry[candidate.vnum] = candidate

    east = Exit(vnum=9591, exit_info=EX_ISDOOR | EX_CLOSED, keyword="gate")
    west = Exit(vnum=9590, exit_info=EX_ISDOOR | EX_CLOSED, keyword="gate")
    east.to_room = other
    west.to_room = room
    room.exits[int(Direction.EAST)] = east
    other.exits[int(Direction.WEST)] = west
    return room, other


def _make_pc(room: Room) -> Character:
    pc = Character(
        name="opener",
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
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
    proto = MobIndex(vnum=9592, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="opens",
            code='mob echo "OPEN_SEEN"\n',
            vnum=9592,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def test_do_open_door_fires_act_trigger_on_listening_npc():
    """ROM src/act_move.c:436 act() with no MOBtrigger wrap dispatches TRIG_ACT."""
    import mud.mobprog as mobprog

    room, _other = _make_rooms()
    pc = _make_pc(room)
    _make_listener(room)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_open(pc, "east")
    finally:
        mobprog.mp_act_trigger = original

    assert fired, (
        "do_open must dispatch mp_act_trigger on its TO_ROOM door broadcast — "
        "ROM src/act_move.c:436, no MOBtrigger wrap"
    )
    assert fired[0][0] == "watcher"
    assert "opens" in fired[0][1]
