"""INV-025 sweep — say/tell act() lines dispatch TRIG_ACT.

ROM ``src/comm.c:2384`` — inside ``act()``/``act_new()``, every NPC
recipient with ``TRIG_ACT`` receives ``mp_act_trigger(buf, to, ch, arg1,
arg2, TRIG_ACT)`` when the global ``MOBtrigger`` is TRUE. ``do_say`` and
``do_tell`` also have explicit ``TRIG_SPEECH`` hooks, but those are separate
from the act()-level ACT trigger dispatch.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from mud.commands.communication import do_say, do_tell
from mud.models.character import Character, character_registry
from mud.models.constants import Position, Sector
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _cleanup():
    from mud import registry

    snapshot = list(character_registry)
    character_registry.clear()
    prev_char_list = list(getattr(registry, "char_list", []))
    prev_players = dict(getattr(registry, "players", {})) if hasattr(registry, "players") else {}
    registry.char_list = []
    registry.players = {}
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    registry.char_list = prev_char_list
    registry.players = prev_players
    room_registry.pop(9800, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(
        vnum=9800,
        name="Speech Test",
        description="",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
    room_registry[9800] = room
    return room


def _make_pc(room: Room, name: str = "speaker") -> Character:
    from mud import registry

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
    room.people.append(pc)
    character_registry.append(pc)
    registry.char_list.append(pc)
    registry.players[name.lower()] = pc
    return pc


def _make_act_listener(room: Room, phrase: str, name: str = "listener") -> Character:
    from mud.mobprog import Trigger

    listener = Character(
        name=name,
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    listener.inventory = []
    listener.equipment = {}
    proto = MobIndex(vnum=9801, short_descr="a listener", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase=phrase,
            code='mob echo "ACT_SEEN"\n',
            vnum=9801,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _recorded_act_triggers(call: Callable[[], object]) -> list[tuple[str, str]]:
    import mud.mobprog as mobprog

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        trigger = kwargs.get("trigger")
        if trigger is None:
            trigger = args[2] if len(args) >= 3 else mobprog.Trigger.ACT
        if trigger == mobprog.Trigger.ACT:
            fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        call()
    finally:
        mobprog.mp_act_trigger = original
    return fired


def test_say_room_act_fires_act_trigger_on_npc_listener():
    """ROM src/act_comm.c:776 / src/comm.c:2384 — say TO_ROOM act() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_act_listener(room, "says", name="listener")

    fired = _recorded_act_triggers(lambda: do_say(pc, "hello there"))

    listener_triggers = [(n, m) for n, m in fired if n == "listener" and "says" in m.lower()]
    assert listener_triggers, (
        f"do_say must dispatch TRIG_ACT for its unsuppressed TO_ROOM act() (ROM src/act_comm.c:776); fired: {fired}"
    )


def test_tell_to_npc_act_fires_act_trigger_on_npc_target():
    """ROM src/act_comm.c:942 / src/comm.c:2384 — tell TO_VICT act_new() fires TRIG_ACT."""
    room = _make_room()
    pc = _make_pc(room)
    _make_act_listener(room, "tells you", name="listener")

    fired = _recorded_act_triggers(lambda: do_tell(pc, "listener keep watch"))

    listener_triggers = [(n, m) for n, m in fired if n == "listener" and "tells you" in m.lower()]
    assert listener_triggers, (
        "do_tell must dispatch TRIG_ACT for its unsuppressed TO_VICT act_new() "
        f"(ROM src/act_comm.c:942); fired: {fired}"
    )
