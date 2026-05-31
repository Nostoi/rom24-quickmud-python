"""INV-025 sweep — do_close/do_lock/do_unlock/do_pick fire mp_act_trigger.

Sibling of `test_inv025_do_open_act_trigger_dispatch.py`. ROM emits the
actor-room line for each door command via `act(..., TO_ROOM)` with NO
`MOBtrigger=FALSE` wrap, so per `src/comm.c:2384` every NPC recipient with a
matching `TRIG_ACT` mobprog must receive `mp_act_trigger`:

    do_close   src/act_move.c:534   act("$n closes the $d.", ...)
    do_lock    src/act_move.c:690   act("$n locks the $d.", ...)
    do_unlock  src/act_move.c:825   act("$n unlocks the $d.", ...)
    do_pick    src/act_move.c:981   act("$n picks the $d.", ...)

Python previously routed these through plain `broadcast_room`, so listening
NPCs silently no-opped (the do_open follow-up gap, now closed for the family).

The reverse-side ("The $d closes." in the linked room) broadcast stays a plain
`broadcast_room`, matching the deliberate do_open precedent (line 209).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.commands.doors import do_close, do_lock, do_pick, do_unlock
from mud.models.character import Character, character_registry
from mud.models.constants import (
    EX_CLOSED,
    EX_ISDOOR,
    EX_LOCKED,
    Direction,
    Position,
)
from mud.models.mob import MobIndex
from mud.models.room import Exit, Room
from mud.registry import room_registry

_KEY_VNUM = 9599


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
    east.key = _KEY_VNUM
    west.key = _KEY_VNUM
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
    # has_key() match for lock/unlock, and the pick-lock skill for do_pick.
    pc.inventory = [SimpleNamespace(vnum=_KEY_VNUM, prototype=None)]
    pc.skills = {"pick lock": 100}
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


def _run_with_probe(command, pc, arg: str) -> list[tuple[str, str]]:
    import mud.mobprog as mobprog

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        command(pc, arg)
    finally:
        mobprog.mp_act_trigger = original
    return fired


def test_do_close_door_fires_act_trigger_on_listening_npc():
    """ROM src/act_move.c:534 — no MOBtrigger wrap → TRIG_ACT dispatch."""
    room, _other = _make_rooms(EX_ISDOOR)  # open door
    pc = _make_pc(room)
    _make_listener(room, "closes")

    fired = _run_with_probe(do_close, pc, "east")

    assert fired, "do_close must dispatch mp_act_trigger on its TO_ROOM door broadcast"
    assert fired[0][0] == "watcher"
    assert "closes" in fired[0][1]


def test_do_lock_door_fires_act_trigger_on_listening_npc():
    """ROM src/act_move.c:690 — no MOBtrigger wrap → TRIG_ACT dispatch."""
    room, _other = _make_rooms(EX_ISDOOR | EX_CLOSED)  # closed, unlocked
    pc = _make_pc(room)
    _make_listener(room, "locks")

    fired = _run_with_probe(do_lock, pc, "east")

    assert fired, "do_lock must dispatch mp_act_trigger on its TO_ROOM door broadcast"
    assert fired[0][0] == "watcher"
    assert "locks" in fired[0][1]


def test_do_unlock_door_fires_act_trigger_on_listening_npc():
    """ROM src/act_move.c:825 — no MOBtrigger wrap → TRIG_ACT dispatch."""
    room, _other = _make_rooms(EX_ISDOOR | EX_CLOSED | EX_LOCKED)  # closed, locked
    pc = _make_pc(room)
    _make_listener(room, "unlocks")

    fired = _run_with_probe(do_unlock, pc, "east")

    assert fired, "do_unlock must dispatch mp_act_trigger on its TO_ROOM door broadcast"
    assert fired[0][0] == "watcher"
    assert "unlocks" in fired[0][1]


def test_do_pick_door_fires_act_trigger_on_listening_npc():
    """ROM src/act_move.c:981 — no MOBtrigger wrap → TRIG_ACT dispatch."""
    from mud.utils import rng_mm

    room, _other = _make_rooms(EX_ISDOOR | EX_CLOSED | EX_LOCKED)  # closed, locked
    pc = _make_pc(room)
    _make_listener(room, "picks")

    # skill_level 100 means number_percent() (1..100) is never > skill → pick succeeds.
    rng_mm.seed_mm(12345)
    fired = _run_with_probe(do_pick, pc, "east")

    assert fired, "do_pick must dispatch mp_act_trigger on its TO_ROOM door broadcast"
    assert fired[0][0] == "watcher"
    assert "picks" in fired[0][1]
