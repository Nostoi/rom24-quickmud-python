"""INV-025 sweep — do_give wraps act() broadcasts in MOBtrigger=FALSE.

ROM contract (``src/act_obj.c:832-836``):

    MOBtrigger = FALSE;
    act ("$n gives $p to $N.", ch, obj, victim, TO_NOTVICT);
    act ("$n gives you $p.",  ch, obj, victim, TO_VICT);
    act ("You give $p to $N.", ch, obj, victim, TO_CHAR);
    MOBtrigger = TRUE;

The explicit ``mp_give_trigger`` covers the give event; the broadcast
act() lines must NOT fan out to TRIG_ACT.  Pre-sweep Python had no
act-trigger dispatch in the broadcast path *at all*, so the suppression
was accidental — wiring INV-025's ``mp_act_trigger_room`` into the
give broadcast would silently regress unless ``disable_mobtrigger()``
wraps it.  This test locks the wrapper.
"""

from __future__ import annotations

import pytest

from mud.commands.give import do_give
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
    room_registry.pop(9510, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9510, name="Vault", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9510] = room
    return room


def _make_pc(room: Room, name: str = "giver") -> Character:
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
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_recipient(room: Room) -> Character:
    npc = Character(
        name="recipient",
        is_npc=True,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    npc.messages = []
    npc.inventory = []
    npc.equipment = {}
    room.people.append(npc)
    character_registry.append(npc)
    return npc


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
    proto = MobIndex(vnum=9511, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="gives",
            code='mob echo "GIVE_SEEN"\n',
            vnum=9511,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _make_obj(holder: Character) -> Object:
    proto = ObjIndex(vnum=9512, short_descr="a token", name="token")
    proto.weight = 1
    obj = Object(instance_id=None, prototype=proto)
    obj.wear_flags = 0
    obj.extra_flags = 0
    holder.inventory.append(obj)
    obj.carried_by = holder
    return obj


def test_do_give_broadcast_dispatches_but_suppresses_act_trigger():
    """ROM src/act_obj.c:832-836 — broadcast dispatches act() per recipient
    (wired via ``mp_act_trigger_room``) but the surrounding
    ``MOBtrigger=FALSE`` (Python ``disable_mobtrigger()``) blocks
    TRIG_ACT fan-out.  Both halves of the contract must hold.
    """
    import mud.commands.give as give_module
    import mud.mobprog as mobprog

    room = _make_room()
    giver = _make_pc(room, name="giver")
    recipient = _make_recipient(room)
    _make_listener(room)
    obj = _make_obj(giver)

    triggered: list[tuple[str, str]] = []
    dispatch_calls: list[str] = []
    original_trigger = mobprog.mp_act_trigger
    original_dispatch = mobprog.mp_act_trigger_room

    def _trigger_probe(argument, mob, ch, *args, **kwargs):
        triggered.append((getattr(mob, "name", "?"), str(argument)))
        return original_trigger(argument, mob, ch, *args, **kwargs)

    def _dispatch_probe(message, *args, **kwargs):
        dispatch_calls.append(str(message))
        return original_dispatch(message, *args, **kwargs)

    mobprog.mp_act_trigger = _trigger_probe
    mobprog.mp_act_trigger_room = _dispatch_probe
    if hasattr(give_module, "mp_act_trigger_room"):
        give_module.mp_act_trigger_room = _dispatch_probe
    try:
        do_give(giver, f"{obj.name} {recipient.name}")
    finally:
        mobprog.mp_act_trigger = original_trigger
        mobprog.mp_act_trigger_room = original_dispatch
        if hasattr(give_module, "mp_act_trigger_room"):
            give_module.mp_act_trigger_room = original_dispatch

    assert dispatch_calls, (
        "do_give broadcast must call mp_act_trigger_room to mirror "
        "ROM src/comm.c:2384 — wiring missing"
    )
    assert triggered == [], (
        f"do_give must wrap its act() broadcast in disable_mobtrigger() "
        f"to mirror ROM src/act_obj.c:832-836; fired: {triggered}"
    )
