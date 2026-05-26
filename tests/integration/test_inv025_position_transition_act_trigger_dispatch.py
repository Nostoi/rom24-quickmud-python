"""INV-025 sweep — position-transition broadcasts fire mp_act_trigger.

ROM contract (``src/fight.c:837-861``): position changes from damage()
broadcast TO_ROOM via act() with no MOBtrigger wrap, so per
``src/comm.c:2384`` every NPC recipient with ``HAS_TRIGGER(TRIG_ACT)``
matching the message must receive ``mp_act_trigger``.

Locks the dispatch through the central ``_broadcast_pos_change`` helper
used by every Python position-transition site (apply_position_change,
spell holy_word, decay_corpse, etc.).
"""

from __future__ import annotations

import pytest

from mud.combat.engine import apply_position_change
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
    room_registry.pop(9570, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9570, name="Arena", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9570] = room
    return room


def _make_victim(room: Room) -> Character:
    victim = Character(
        name="victim",
        is_npc=False,
        level=10,
        room=room,
        position=int(Position.STUNNED),
        default_pos=int(Position.STANDING),
        hit=-7,
        max_hit=100,
    )
    victim.messages = []
    room.people.append(victim)
    character_registry.append(victim)
    return victim


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
    proto = MobIndex(vnum=9571, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="mortally",
            code='mob echo "POS_SEEN"\n',
            vnum=9571,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def test_position_transition_fires_act_trigger_on_listening_npc():
    """ROM src/fight.c:837-838 act() with no MOBtrigger wrap dispatches TRIG_ACT."""
    import mud.mobprog as mobprog

    room = _make_room()
    victim = _make_victim(room)
    _make_listener(room)
    # MORTAL threshold is hit <= -6
    victim.hit = -7
    victim.position = Position.MORTAL

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        apply_position_change(victim, Position.STUNNED)
    finally:
        mobprog.mp_act_trigger = original

    assert fired, (
        "position transition must dispatch mp_act_trigger on its TO_ROOM "
        "broadcast — ROM src/fight.c:837-861, no MOBtrigger wrap"
    )
    assert "mortally" in fired[0][1].lower()
