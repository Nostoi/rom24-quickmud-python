"""INV-025 sweep — movement departure and arrival fire mp_act_trigger.

ROM contract (``src/act_move.c:197,202``):
``move_char`` emits ``act("$n leaves $T.", ch, NULL, dir_name[door], TO_ROOM)``
from the old room and ``act("$n has arrived.", ch, NULL, NULL, TO_ROOM)`` from
the new room.  Neither is wrapped in ``MOBtrigger = FALSE``, so per
``src/comm.c:2384`` every NPC recipient with ``HAS_TRIGGER(TRIG_ACT)``
matching the message must receive ``mp_act_trigger``.

Portal entry/exit broadcasts (``src/act_enter.c:134,151``) similarly use
``act(TO_ROOM)`` without a ``MOBtrigger`` wrap.

Locks the contract for:
  - Directional movement departure  (act_move.c:197)
  - Directional movement arrival    (act_move.c:202)
  - Directional movement PERS masking before delivery / TRIG_ACT
  - Portal entry departure          (act_enter.c:134)
  - Portal entry arrival            (act_enter.c:151)
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import (
    AffectFlag,
    Direction,
    ItemType,
    PortalFlag,
    Position,
)
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.registry import room_registry
from mud.world.movement import move_character, move_character_through_portal


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    for vnum in (9570, 9571, 9572):
        room_registry.pop(vnum, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room(vnum: int, name: str = "Room") -> Room:
    room = Room(vnum=vnum, name=name, description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room.exits = [None] * 6
    room_registry[vnum] = room
    return room


def _make_pc(room: Room, name: str = "mover") -> Character:
    pc = Character(
        name=name,
        is_npc=False,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    pc.inventory = []
    pc.equipment = {}
    pc.alignment = 0
    pc.size = 3
    pc.move = 100
    pc.max_move = 100
    pc.hit = 100
    pc.max_hit = 100
    pc.mana = 100
    pc.max_mana = 100
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room, phrase: str, vnum: int = 9572) -> Character:
    from mud.mobprog import Trigger

    listener = Character(
        name=f"watcher_{vnum}",
        is_npc=True,
        level=5,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=vnum, short_descr="a watcher", level=5)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase=phrase,
            code='mob echo "MOVE_SEEN"\n',
            vnum=vnum,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _connect_rooms(src: Room, dst: Room, direction: Direction) -> None:
    rev = {
        Direction.NORTH: Direction.SOUTH,
        Direction.SOUTH: Direction.NORTH,
        Direction.EAST: Direction.WEST,
        Direction.WEST: Direction.EAST,
        Direction.UP: Direction.DOWN,
        Direction.DOWN: Direction.UP,
    }
    fwd_exit = Exit(vnum=dst.vnum, exit_info=0, keyword="")
    fwd_exit.to_room = dst
    rev_exit = Exit(vnum=src.vnum, exit_info=0, keyword="")
    rev_exit.to_room = src
    src.exits[int(direction)] = fwd_exit
    dst.exits[int(rev[direction])] = rev_exit


class TestDirectionalDepartureArrival:
    def test_departure_fires_act_trigger_on_listening_npc(self):
        import mud.mobprog as mobprog

        room_a = _make_room(9570, "Room A")
        room_b = _make_room(9571, "Room B")
        _connect_rooms(room_a, room_b, Direction.NORTH)
        pc = _make_pc(room_a)
        _make_listener(room_a, "leaves")

        fired: list[tuple[str, str]] = []
        original = mobprog.mp_act_trigger

        def _probe(argument, mob, ch, *args, **kwargs):
            fired.append((getattr(mob, "name", "?"), str(argument)))
            return original(argument, mob, ch, *args, **kwargs)

        mobprog.mp_act_trigger = _probe
        try:
            move_character(pc, "north")
        finally:
            mobprog.mp_act_trigger = original

        assert fired, (
            "move_character departure must dispatch mp_act_trigger on its "
            "TO_ROOM broadcast — ROM src/act_move.c:197, no MOBtrigger wrap"
        )
        assert "leaves" in fired[0][1]

    def test_arrival_fires_act_trigger_on_listening_npc(self):
        import mud.mobprog as mobprog

        room_a = _make_room(9570, "Room A")
        room_b = _make_room(9571, "Room B")
        _connect_rooms(room_a, room_b, Direction.NORTH)
        pc = _make_pc(room_a)
        _make_listener(room_b, "arrived")

        fired: list[tuple[str, str]] = []
        original = mobprog.mp_act_trigger

        def _probe(argument, mob, ch, *args, **kwargs):
            fired.append((getattr(mob, "name", "?"), str(argument)))
            return original(argument, mob, ch, *args, **kwargs)

        mobprog.mp_act_trigger = _probe
        try:
            move_character(pc, "north")
        finally:
            mobprog.mp_act_trigger = original

        assert fired, (
            "move_character arrival must dispatch mp_act_trigger on its "
            "TO_ROOM broadcast — ROM src/act_move.c:202, no MOBtrigger wrap"
        )
        assert "arrived" in fired[0][1]

    def test_sneaking_does_not_fire_act_trigger(self):
        import mud.mobprog as mobprog

        room_a = _make_room(9570, "Room A")
        room_b = _make_room(9571, "Room B")
        _connect_rooms(room_a, room_b, Direction.NORTH)
        pc = _make_pc(room_a)
        from mud.models.constants import AffectFlag

        pc.affected_by = int(AffectFlag.SNEAK)

        _make_listener(room_a, "leaves")

        fired: list[tuple[str, str]] = []
        original = mobprog.mp_act_trigger

        def _probe(argument, mob, ch, *args, **kwargs):
            fired.append((getattr(mob, "name", "?"), str(argument)))
            return original(argument, mob, ch, *args, **kwargs)

        mobprog.mp_act_trigger = _probe
        try:
            move_character(pc, "north")
        finally:
            mobprog.mp_act_trigger = original

        act_fired = [f for f in fired if f[0] != "__greet__"]
        assert not act_fired, (
            "Sneaking characters suppress the departure/arrival broadcast "
            "and must NOT fire TRIG_ACT — ROM act_move.c:197 guards on "
            "!IS_AFFECTED(ch, AFF_SNEAK) && ch->invis_level < LEVEL_HERO"
        )

    def test_departure_uses_per_recipient_pers_masking(self):
        room_a = _make_room(9570, "Room A")
        room_b = _make_room(9571, "Room B")
        _connect_rooms(room_a, room_b, Direction.NORTH)
        pc = _make_pc(room_a, name="HiddenMover")
        pc.affected_by = int(AffectFlag.INVISIBLE)
        watcher = _make_pc(room_a, name="Watcher")

        # mirrors ROM src/act_move.c:197 — act("$n leaves $T.", ..., TO_ROOM)
        # renders $n through PERS(ch, to), so an unaided watcher sees "Someone".
        move_character(pc, "north")

        assert "Someone leaves north." in watcher.messages
        assert "HiddenMover leaves north." not in watcher.messages


class TestPortalEntry:
    def test_portal_departure_fires_act_trigger(self):
        import mud.mobprog as mobprog

        room_a = _make_room(9570, "Room A")
        room_b = _make_room(9571, "Room B")
        pc = _make_pc(room_a)
        _make_listener(room_a, "steps")

        proto = ObjIndex(vnum=9580, short_descr="a glowing portal", name="portal")
        proto.item_type = int(ItemType.PORTAL)
        proto.wear_flags = 0
        proto.value = [3, 0, 0, 0, 0]
        portal = Object(instance_id=None, prototype=proto)
        portal.value = [3, 0, int(PortalFlag.NORMAL_EXIT) | int(PortalFlag.GOWITH), room_b.vnum, 0]
        room_a.add_object(portal)

        fired: list[tuple[str, str]] = []
        original = mobprog.mp_act_trigger

        def _probe(argument, mob, ch, *args, **kwargs):
            fired.append((getattr(mob, "name", "?"), str(argument)))
            return original(argument, mob, ch, *args, **kwargs)

        mobprog.mp_act_trigger = _probe
        try:
            move_character_through_portal(pc, portal)
        finally:
            mobprog.mp_act_trigger = original

        assert fired, (
            "Portal departure must dispatch mp_act_trigger on its TO_ROOM "
            "broadcast — ROM src/act_enter.c:134, no MOBtrigger wrap"
        )
        assert any("steps" in msg for _, msg in fired)

    def test_portal_arrival_fires_act_trigger(self):
        import mud.mobprog as mobprog

        room_a = _make_room(9570, "Room A")
        room_b = _make_room(9571, "Room B")
        pc = _make_pc(room_a)
        _make_listener(room_b, "arrived")

        proto = ObjIndex(vnum=9580, short_descr="a glowing portal", name="portal")
        proto.item_type = int(ItemType.PORTAL)
        proto.wear_flags = 0
        proto.value = [3, 0, 0, 0, 0]
        portal = Object(instance_id=None, prototype=proto)
        portal.value = [3, 0, int(PortalFlag.NORMAL_EXIT) | int(PortalFlag.GOWITH), room_b.vnum, 0]
        room_a.add_object(portal)

        fired: list[tuple[str, str]] = []
        original = mobprog.mp_act_trigger

        def _probe(argument, mob, ch, *args, **kwargs):
            fired.append((getattr(mob, "name", "?"), str(argument)))
            return original(argument, mob, ch, *args, **kwargs)

        mobprog.mp_act_trigger = _probe
        try:
            move_character_through_portal(pc, portal)
        finally:
            mobprog.mp_act_trigger = original

        assert fired, (
            "Portal arrival must dispatch mp_act_trigger on its TO_ROOM "
            "broadcast — ROM src/act_enter.c:151, no MOBtrigger wrap"
        )
        assert any("arrived" in msg for _, msg in fired)


class TestQuitBroadcast:
    def test_quit_fires_act_trigger(self):
        """ROM src/act_comm.c:1482 act("$n has left the game.", ch, NULL, NULL, TO_ROOM)."""
        import mud.mobprog as mobprog

        room = _make_room(9570, "Room")
        pc = _make_pc(room)
        _make_listener(room, "left")

        fired: list[tuple[str, str]] = []
        original = mobprog.mp_act_trigger

        def _probe(argument, mob, ch, *args, **kwargs):
            fired.append((getattr(mob, "name", "?"), str(argument)))
            return original(argument, mob, ch, *args, **kwargs)

        mobprog.mp_act_trigger = _probe
        try:
            from mud.commands.session import do_quit

            do_quit(pc, "")
        finally:
            mobprog.mp_act_trigger = original

        assert fired, (
            "do_quit must dispatch mp_act_trigger on its TO_ROOM broadcast — "
            "ROM src/act_comm.c:1482, no MOBtrigger wrap"
        )
        assert "left" in fired[0][1]


class TestScanPeerBroadcast:
    def test_scan_all_fires_act_trigger(self):
        """ROM src/scan.c:60 act("$n looks all around.", ch, NULL, NULL, TO_ROOM)."""
        import mud.mobprog as mobprog

        room = _make_room(9570, "Room")
        pc = _make_pc(room)
        _make_listener(room, "looks")

        fired: list[tuple[str, str]] = []
        original = mobprog.mp_act_trigger

        def _probe(argument, mob, ch, *args, **kwargs):
            fired.append((getattr(mob, "name", "?"), str(argument)))
            return original(argument, mob, ch, *args, **kwargs)

        mobprog.mp_act_trigger = _probe
        try:
            from mud.commands.inspection import do_scan

            do_scan(pc, "")
        finally:
            mobprog.mp_act_trigger = original

        assert fired, (
            "do_scan (look all) must dispatch mp_act_trigger on its TO_ROOM "
            "broadcast — ROM src/scan.c:60, no MOBtrigger wrap"
        )
        assert "looks" in fired[0][1]

    def test_scan_direction_fires_act_trigger(self):
        """ROM src/scan.c:90 act("$n peers intently $T.", ch, NULL, dir_name, TO_ROOM)."""
        import mud.mobprog as mobprog

        room = _make_room(9570, "Room")
        # Need exits for directional scan to work
        other = _make_room(9571, "Other")
        east = Exit(vnum=9571, exit_info=0, keyword="")
        east.to_room = other
        room.exits[int(Direction.EAST)] = east

        pc = _make_pc(room)
        _make_listener(room, "peers")

        fired: list[tuple[str, str]] = []
        original = mobprog.mp_act_trigger

        def _probe(argument, mob, ch, *args, **kwargs):
            fired.append((getattr(mob, "name", "?"), str(argument)))
            return original(argument, mob, ch, *args, **kwargs)

        mobprog.mp_act_trigger = _probe
        try:
            from mud.commands.inspection import do_scan

            do_scan(pc, "east")
        finally:
            mobprog.mp_act_trigger = original

        assert fired, (
            "do_scan (direction) must dispatch mp_act_trigger on its TO_ROOM "
            "broadcast — ROM src/scan.c:90, no MOBtrigger wrap"
        )
        assert "peers" in fired[0][1]
