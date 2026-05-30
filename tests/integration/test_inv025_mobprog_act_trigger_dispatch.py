"""INV-025 — MOBPROG-ACT-TRIGGER-DISPATCH.

ROM contract: ``src/comm.c:2384-2385`` — inside ``act()``, every NPC
recipient with ``HAS_TRIGGER(TRIG_ACT)`` receives ``mp_act_trigger`` on
the formatted message.  The dispatch is gated on the global
``bool MOBtrigger`` flag (``src/comm.c:311``) so recursive paths that
themselves call ``act()`` (do_give, do_at, do_mob, …) can suppress
re-entry by toggling ``MOBtrigger = FALSE`` around their own act() calls.

Python ``do_emote`` (``mud/commands/communication.py:do_emote``) is the
textbook ROM TRIG_ACT producer — ``act("$n $T", ch, NULL, argument,
TO_ROOM)``.  Pre-INV-025 Python fanned the emote string out to listener
sockets but did not dispatch to ``mp_act_trigger``; every TRIG_ACT
mobprog responding to PC emotes silently no-opped.

This test locks two contracts:

1. PC emote in a room containing an NPC with TRIG_ACT and matching
   ``trig_phrase`` fires ``mp_act_trigger`` exactly once on the listener.
2. With the ``disable_mobtrigger()`` context manager active (the
   Python port of ROM's ``MOBtrigger = FALSE``), the same emote does
   NOT fire ``mp_act_trigger`` — mirroring ROM's recursion guard at
   ``src/act_obj.c:832-836`` and ``src/mob_cmds.c:333-335``.
"""

from __future__ import annotations

import pytest

from mud.commands.communication import do_emote
from mud.commands.position import do_stand
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9500, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int = 9501):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9500, name="Bow", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9500] = room
    return room


def _make_pc(room: Room) -> Character:
    pc = Character(
        name="emoter",
        is_npc=False,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room) -> Character:
    listener = Character(
        name="listener",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=9501, short_descr="a listener", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(_act_trigger_flag()),
            trig_phrase="bows",
            code='mob echo "ACT_TRIGGERED"\n',
            vnum=9501,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _act_trigger_flag() -> int:
    from mud.mobprog import Trigger

    return int(Trigger.ACT)


def test_pc_emote_fires_act_trigger_on_listening_npc():
    """ROM src/comm.c:2384 — PC act() → mp_act_trigger on NPC recipient."""
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_emote(pc, "bows deeply")
    finally:
        mobprog.mp_act_trigger = original

    assert len(fired) == 1, (
        f"expected exactly one mp_act_trigger fire on the listening NPC; "
        f"got: {fired}"
    )
    assert fired[0][0] == "listener"
    assert "bows" in fired[0][1]


def test_disable_mobtrigger_suppresses_act_trigger_dispatch():
    """ROM src/comm.c:311 / src/act_obj.c:832 — MOBtrigger=FALSE blocks dispatch."""
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        with mobprog.disable_mobtrigger():
            do_emote(pc, "bows deeply")
    finally:
        mobprog.mp_act_trigger = original

    assert fired == [], (
        f"MOBtrigger=FALSE must suppress mp_act_trigger dispatch "
        f"(ROM src/comm.c:2384); fired: {fired}"
    )


def test_act_trigger_skipped_when_emoter_is_npc():
    """ROM act() dispatches to all NPC recipients regardless of speaker
    identity — but ``do_emote``'s loop excludes the emoter itself
    (``if listener is char: continue``), so an NPC emoter must not
    self-fire its own ACT trigger.  Lock the no-self-fire contract."""
    import mud.mobprog as mobprog
    from mud.mobprog import Trigger

    room = _make_room()

    npc_emoter = Character(
        name="npc-emoter",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    npc_emoter.messages = []
    proto = MobIndex(vnum=9502, short_descr="an emoter", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="bows",
            code='mob echo "SELF_TRIGGERED"\n',
            vnum=9502,
        )
    ]
    npc_emoter.prototype = proto
    room.people.append(npc_emoter)
    character_registry.append(npc_emoter)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_emote(npc_emoter, "bows deeply")
    finally:
        mobprog.mp_act_trigger = original

    assert fired == [], (
        f"emoter must not self-fire its own TRIG_ACT; fired: {fired}"
    )


def test_position_act_room_broadcast_fires_act_trigger_on_listening_npc():
    """ROM src/act_move.c:1062 / src/comm.c:2384 — stand act() fires TRIG_ACT."""
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    pc.position = Position.RESTING
    _make_listener(room)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_stand(pc, "")
    finally:
        mobprog.mp_act_trigger = original

    assert len(fired) == 1, (
        f"expected exactly one mp_act_trigger fire for the stand room act(); "
        f"got: {fired}"
    )
    assert fired[0][0] == "listener"
    assert "stands" in fired[0][1]
