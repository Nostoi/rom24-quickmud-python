"""INV-025 sweep — do_drop fires mp_act_trigger on listening NPCs.

ROM contract (``src/act_obj.c:606-613, 631-637``):

    act ("$n drops $p.", ch, obj, NULL, TO_ROOM);
    act ("You drop $p.", ch, obj, NULL, TO_CHAR);

ROM does NOT wrap these in ``MOBtrigger=FALSE``, so per ``src/comm.c:2384``
every NPC recipient with ``HAS_TRIGGER(TRIG_ACT)`` matching the message
must receive ``mp_act_trigger``.  Pre-sweep Python broadcast the drop
text but never dispatched to ``mp_act_trigger``, so TRIG_ACT mobprogs
keyed on "drops" silently no-opped.
"""

from __future__ import annotations

import pytest

from mud.commands.inventory import do_drop
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
    room_registry.pop(9520, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9520, name="Alley", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9520] = room
    return room


def _make_pc(room: Room) -> Character:
    pc = Character(
        name="dropper",
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
    proto = MobIndex(vnum=9521, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="drops",
            code='mob echo "DROP_SEEN"\n',
            vnum=9521,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _make_obj(holder: Character) -> Object:
    proto = ObjIndex(vnum=9522, short_descr="a coin", name="coin")
    proto.weight = 1
    obj = Object(instance_id=None, prototype=proto)
    obj.wear_flags = 0
    obj.extra_flags = 0
    obj.wear_loc = -1
    holder.inventory.append(obj)
    obj.carried_by = holder
    return obj


def test_do_drop_fires_act_trigger_on_listening_npc():
    """ROM src/act_obj.c:608 act() with no MOBtrigger wrap dispatches TRIG_ACT."""
    import mud.commands.inventory as inv_module
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room)
    obj = _make_obj(pc)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_drop(pc, obj.name or "coin")
    finally:
        mobprog.mp_act_trigger = original

    _ = inv_module  # keep import alive for diagnostics
    assert fired, (
        "do_drop must dispatch mp_act_trigger on its TO_ROOM broadcast — "
        "ROM src/act_obj.c:608, no MOBtrigger wrap"
    )
    assert fired[0][0] == "watcher"
    assert "drops" in fired[0][1]
