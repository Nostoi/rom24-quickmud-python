"""INV-025 door-command PERS sweep — ``_broadcast_act_to_room`` baked the actor.

ROM emits the actor-room line for each door command via ``act("$n …", TO_ROOM)``
(``src/act_move.c`` open/close/lock/unlock/pick), so ``$n`` renders through
``PERS(ch, looker)`` per recipient — an invisible actor masks to "Someone"
(INV-027). The Python ``doors._broadcast_act_to_room`` chokepoint took a
pre-baked ``f"{actor_name} …"`` string, so it delivered the actor's identity
to every witness un-masked (it did already dispatch TRIG_ACT). This sweep
reworks the helper to take a ``$n``/``$p``/``$d`` format string and route
through ``act_to_room`` for per-recipient PERS.

Covers both substitution shapes: ``$p`` (portal/container object) and ``$d``
(door keyword).
"""

from __future__ import annotations

import pytest

from mud.commands.doors import do_close, do_lock, do_open, do_pick
from mud.models.character import Character, character_registry
from mud.models.constants import (
    EX_CLOSED,
    EX_ISDOOR,
    EX_LOCKED,
    AffectFlag,
    ContainerFlag,
    Direction,
    ItemType,
    Position,
)
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.registry import room_registry

_KEY_VNUM = 9698


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9690, None)
    room_registry.pop(9691, None)


def _rooms(exit_info: int) -> tuple[Room, Room]:
    room = Room(vnum=9690, name="Entry", description="", room_flags=0, sector_type=0)
    other = Room(vnum=9691, name="Hall", description="", room_flags=0, sector_type=0)
    for c in (room, other):
        c.people = []
        c.contents = []
        c.exits = [None] * 6
        room_registry[c.vnum] = c
    east = Exit(vnum=9691, exit_info=exit_info, keyword="gate")
    west = Exit(vnum=9690, exit_info=exit_info, keyword="gate")
    east.to_room = other
    west.to_room = room
    east.key = _KEY_VNUM
    west.key = _KEY_VNUM
    room.exits[int(Direction.EAST)] = east
    other.exits[int(Direction.WEST)] = west
    return room, other


def _actor(room: Room, *, invisible: bool) -> Character:
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
    ch.skills = {"pick lock": 100}
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


def _container(room: Room, *, closed: bool, locked: bool = False) -> Object:
    flags = int(ContainerFlag.CLOSEABLE)
    if closed:
        flags |= int(ContainerFlag.CLOSED)
    if locked:
        flags |= int(ContainerFlag.LOCKED)
    proto = ObjIndex(
        vnum=9692,
        name="bag",
        short_descr="a leather bag",
        item_type=int(ItemType.CONTAINER),
        value=[100, flags, _KEY_VNUM, 0, 0],
    )
    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = int(ItemType.CONTAINER)
    obj.value = [100, flags, _KEY_VNUM, 0, 0]
    obj.in_room = room
    room.contents.append(obj)
    return obj


def _line(w: Character) -> str:
    return "\n".join(w.messages)


# ---- $p (container/portal object) ----------------------------------------


def test_open_container_masks_invisible_actor():
    room, _ = _rooms(0)
    ch = _actor(room, invisible=True)
    w = _witness(room)
    _container(room, closed=True)
    w.messages.clear()

    do_open(ch, "bag")

    assert "Someone opens a leather bag." in _line(w), w.messages


def test_open_container_shows_name_to_sighted_witness():
    room, _ = _rooms(0)
    ch = _actor(room, invisible=False)
    w = _witness(room)
    _container(room, closed=True)
    w.messages.clear()

    do_open(ch, "bag")

    assert "Glark opens a leather bag." in _line(w), w.messages


def test_close_container_masks_invisible_actor():
    room, _ = _rooms(0)
    ch = _actor(room, invisible=True)
    w = _witness(room)
    _container(room, closed=False)
    w.messages.clear()

    do_close(ch, "bag")

    assert "Someone closes a leather bag." in _line(w), w.messages


def test_lock_container_masks_invisible_actor():
    room, _ = _rooms(0)
    ch = _actor(room, invisible=True)
    w = _witness(room)
    obj = _container(room, closed=True)
    ch.inventory = [obj.__class__(instance_id=None, prototype=ObjIndex(vnum=_KEY_VNUM, name="key"))]
    w.messages.clear()

    do_lock(ch, "bag")

    assert "Someone locks a leather bag." in _line(w), w.messages


# ---- $d (door keyword) -----------------------------------------------------


def test_open_door_masks_invisible_actor():
    room, _ = _rooms(EX_ISDOOR | EX_CLOSED)
    ch = _actor(room, invisible=True)
    w = _witness(room)
    w.messages.clear()

    do_open(ch, "gate")

    assert "Someone opens the gate." in _line(w), w.messages


def test_open_door_shows_name_to_sighted_witness():
    room, _ = _rooms(EX_ISDOOR | EX_CLOSED)
    ch = _actor(room, invisible=False)
    w = _witness(room)
    w.messages.clear()

    do_open(ch, "gate")

    assert "Glark opens the gate." in _line(w), w.messages


def test_pick_door_masks_invisible_actor():
    room, _ = _rooms(EX_ISDOOR | EX_CLOSED | EX_LOCKED)
    ch = _actor(room, invisible=True)
    # has_key() not required for pick; pick-lock skill is set in _actor.
    w = _witness(room)
    w.messages.clear()

    do_pick(ch, "gate")

    assert "Someone picks the gate." in _line(w), w.messages
