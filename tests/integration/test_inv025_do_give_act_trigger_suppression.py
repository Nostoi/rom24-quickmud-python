"""INV-025 sweep — do_give wraps act() broadcasts in MOBtrigger=FALSE.

ROM contract (``src/act_obj.c:832-836``):

    MOBtrigger = FALSE;
    act ("$n gives $p to $N.", ch, obj, victim, TO_NOTVICT);
    act ("$n gives you $p.",  ch, obj, victim, TO_VICT);
    act ("You give $p to $N.", ch, obj, victim, TO_CHAR);
    MOBtrigger = TRUE;

The explicit ``mp_give_trigger`` covers the give event; the broadcast
act() lines must NOT fan out to TRIG_ACT.  Two behavioral halves must
hold: (1) the TO_NOTVICT line is delivered to room observers, and
(2) no TRIG_ACT fires on a listening NPC.  As of the 2.12.54 PERS sweep
the object branch renders through ``act_to_room`` wrapped in
``disable_mobtrigger()`` — ``act_to_room`` gates its own per-recipient
``mp_act_trigger`` dispatch on the ``MOBtrigger`` global, so the wrapper
is what keeps the suppression.  This test locks the wrapper behaviorally
(it no longer asserts the obsolete ``mp_act_trigger_room`` call shape,
which the ``act_to_room`` refactor replaced).
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
    """ROM src/act_obj.c:832-836 — the give TO_NOTVICT line is delivered to room
    observers, but the surrounding ``MOBtrigger=FALSE`` (Python
    ``disable_mobtrigger()`` wrapping ``act_to_room``) blocks TRIG_ACT fan-out.
    Both behavioral halves must hold.
    """
    import mud.mobprog as mobprog

    room = _make_room()
    giver = _make_pc(room, name="giver")
    recipient = _make_recipient(room)
    listener = _make_listener(room)  # NPC bystander (not the victim) with a "gives" TRIG_ACT
    obj = _make_obj(giver)
    listener.messages.clear()

    triggered: list[tuple[str, str]] = []
    original_trigger = mobprog.mp_act_trigger

    def _trigger_probe(argument, mob, ch, *args, **kwargs):
        triggered.append((getattr(mob, "name", "?"), str(argument)))
        return original_trigger(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _trigger_probe
    try:
        do_give(giver, f"{obj.name} {recipient.name}")
    finally:
        mobprog.mp_act_trigger = original_trigger

    # (1) The TO_NOTVICT line reaches the bystander (act_to_room delivery).
    assert any("gives" in m for m in listener.messages), (
        f"do_give must deliver its TO_NOTVICT act() line to room observers; got {listener.messages}"
    )
    # (2) No TRIG_ACT fires — disable_mobtrigger() gates act_to_room's per-recipient dispatch.
    assert triggered == [], (
        f"do_give must wrap its act() broadcast in disable_mobtrigger() "
        f"to mirror ROM src/act_obj.c:832-836; fired: {triggered}"
    )
