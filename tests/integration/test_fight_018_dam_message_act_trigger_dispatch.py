"""FIGHT-018 — combat dam_message broadcasts fire mp_act_trigger.

ROM contract (``src/fight.c:2215-2226``): ``dam_message`` emits the
combat hit line TO_ROOM (self-inflicted) or TO_NOTVICT (normal) via
``act()`` with no ``MOBtrigger`` wrap, so per ``src/comm.c:2384`` every
NPC recipient in the room with ``HAS_TRIGGER(TRIG_ACT)`` matching the
message receives ``mp_act_trigger``. Before this fix Python rendered
the per-recipient combat text but never dispatched TRIG_ACT, so mob
ACT-progs never responded to combat happening in their room.

Locks the dispatch through ``_broadcast_damage_messages`` (the Python
port of ROM ``dam_message``).
"""

from __future__ import annotations

import pytest

from mud.combat.engine import _broadcast_damage_messages
from mud.combat.messages import DamageMessages
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
    room_registry.pop(9572, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9572, name="Arena", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9572] = room
    return room


def _make_combatant(room: Room, name: str) -> Character:
    char = Character(
        name=name,
        is_npc=False,
        level=10,
        room=room,
        position=int(Position.FIGHTING),
        default_pos=int(Position.STANDING),
        hit=100,
        max_hit=100,
    )
    char.messages = []
    room.people.append(char)
    character_registry.append(char)
    return char


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
    proto = MobIndex(vnum=9573, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="mauls",
            code='mob echo "COMBAT_SEEN"\n',
            vnum=9573,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def test_dam_message_fires_act_trigger_on_listening_npc():
    """ROM src/fight.c:2222 act(TO_NOTVICT) with no MOBtrigger wrap dispatches TRIG_ACT."""
    import mud.mobprog as mobprog

    room = _make_room()
    attacker = _make_combatant(room, "attacker")
    victim = _make_combatant(room, "victim")
    _make_listener(room)

    messages = DamageMessages(
        attacker="You maul {victim}.",
        victim="{attacker} mauls you.",
        room="{attacker} mauls {victim}.",
        self_inflicted=False,
    )

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        _broadcast_damage_messages(attacker, victim, messages)
    finally:
        mobprog.mp_act_trigger = original

    assert fired, (
        "combat dam_message must dispatch mp_act_trigger on its TO_NOTVICT "
        "broadcast — ROM src/fight.c:2215-2226, no MOBtrigger wrap"
    )
    assert fired[0][0] == "watcher"
    assert "mauls" in fired[0][1].lower()


def test_dam_message_act_trigger_excludes_attacker_and_victim():
    """ROM TO_NOTVICT excludes ch and victim; only third-party NPCs fire."""
    import mud.mobprog as mobprog

    room = _make_room()
    attacker = _make_combatant(room, "attacker")
    victim = _make_combatant(room, "victim")
    _make_listener(room)

    messages = DamageMessages(
        attacker="You maul {victim}.",
        victim="{attacker} mauls you.",
        room="{attacker} mauls {victim}.",
        self_inflicted=False,
    )

    recipients: list[str] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        recipients.append(getattr(mob, "name", "?"))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        _broadcast_damage_messages(attacker, victim, messages)
    finally:
        mobprog.mp_act_trigger = original

    assert "attacker" not in recipients
    assert "victim" not in recipients
