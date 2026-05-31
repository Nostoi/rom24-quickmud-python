"""INV-025 sweep — reverse-side door broadcasts fire mp_act_trigger.

Closes the deferred do_open/do_close reverse-side gap. ROM opens/closes the
*linked* room's exit and narrates it per-recipient:

    do_open   src/act_move.c:447-448
        for (rch = to_room->people; ...; rch = rch->next_in_room)
            act("The $d opens.", rch, NULL, pexit_rev->keyword, TO_CHAR);
    do_close  src/act_move.c:545-547
            act("The $d closes.", rch, NULL, pexit_rev->keyword, TO_CHAR);

Because the actor handed to ``act()`` is ``rch`` itself (TO_CHAR collapses the
recipient set to ``{rch}``), the ``src/comm.c:2384`` dispatch fires
``mp_act_trigger(buf, to=rch, ch=rch, ...)`` — i.e. the listening NPC is *both*
the recipient and the actor. Python previously routed this through a plain
``broadcast_room`` (the deliberate do_open precedent), so a far-room NPC with a
matching ``TRIG_ACT`` mobprog silently no-opped.

lock/unlock/pick have no reverse-side broadcast (ROM flips the bit silently),
so this gap is do_open/do_close only.
"""

from __future__ import annotations

import pytest

from mud.commands.doors import do_close, do_open
from mud.models.character import Character, character_registry
from mud.models.constants import (
    EX_CLOSED,
    EX_ISDOOR,
    Direction,
    Position,
)
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


def _make_rooms(exit_info: int) -> tuple[Room, Room]:
    room = Room(vnum=9590, name="Entry", description="", room_flags=0, sector_type=0)
    other = Room(vnum=9591, name="Hall", description="", room_flags=0, sector_type=0)
    for candidate in (room, other):
        candidate.people = []
        candidate.contents = []
        candidate.exits = [None] * 6
        room_registry[candidate.vnum] = candidate

    east = Exit(vnum=9591, exit_info=exit_info, keyword="gate")
    west = Exit(vnum=9590, exit_info=exit_info, keyword="gate")
    east.to_room = other
    west.to_room = room
    room.exits[int(Direction.EAST)] = east
    other.exits[int(Direction.WEST)] = west
    return room, other


def _make_pc(room: Room) -> Character:
    pc = Character(
        name="actor",
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


def _make_listener(room: Room, phrase: str) -> Character:
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
            trig_phrase=phrase,
            code='mob echo "ACT_SEEN"\n',
            vnum=9592,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _run_with_probe(command, pc, arg: str) -> list[tuple[str, object, str]]:
    """Capture (recipient_name, actor, message) for every mp_act_trigger call."""
    import mud.mobprog as mobprog

    fired: list[tuple[str, object, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), ch, str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        command(pc, arg)
    finally:
        mobprog.mp_act_trigger = original
    return fired


def test_do_open_reverse_side_fires_act_trigger_on_linked_room_npc():
    """ROM src/act_move.c:447-448 — far-room NPC sees 'The $d opens.' and the
    actor handed to act() (hence mp_act_trigger) is the NPC itself."""
    room, other = _make_rooms(EX_ISDOOR | EX_CLOSED)  # closed door
    pc = _make_pc(room)
    listener = _make_listener(other, "opens")

    fired = _run_with_probe(do_open, pc, "east")

    assert fired, "do_open reverse side must dispatch mp_act_trigger on the linked-room NPC"
    recipient_name, actor, message = fired[0]
    assert recipient_name == "watcher"
    assert "opens" in message
    # ROM act("The $d opens.", rch, ...) — actor == recipient (TO_CHAR self-dispatch).
    assert actor is listener


def test_do_close_reverse_side_fires_act_trigger_on_linked_room_npc():
    """ROM src/act_move.c:545-547 — far-room NPC sees 'The $d closes.' with
    the NPC itself as the act() actor."""
    room, other = _make_rooms(EX_ISDOOR)  # open door
    pc = _make_pc(room)
    listener = _make_listener(other, "closes")

    fired = _run_with_probe(do_close, pc, "east")

    assert fired, "do_close reverse side must dispatch mp_act_trigger on the linked-room NPC"
    recipient_name, actor, message = fired[0]
    assert recipient_name == "watcher"
    assert "closes" in message
    assert actor is listener
