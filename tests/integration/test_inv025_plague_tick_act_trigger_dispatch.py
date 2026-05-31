"""INV-025 sweep — plague tick act() broadcasts fire mp_act_trigger.

ROM ``src/update.c:803-804`` emits the plague tick room line through
``act(..., TO_ROOM)``. Per ``src/comm.c:2384-2385``, that formatted act()
buffer dispatches ``mp_act_trigger`` to NPC recipients, and ``$n`` is rendered
through ``PERS(ch, to)`` for each recipient.
"""

from __future__ import annotations

import pytest

from mud.models.character import AffectData, Character, character_registry
from mud.models.constants import AffectFlag, Position, Sector, Sex
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
    room_registry.pop(9580, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9580, name="Sickroom", description="", room_flags=0, sector_type=int(Sector.INSIDE))
    room.people = []
    room.contents = []
    room_registry[9580] = room
    return room


def _make_plagued(room: Room) -> Character:
    plagued = Character(
        name="Wraith",
        short_descr="Wraith",
        is_npc=False,
        level=10,
        room=room,
        sex=int(Sex.MALE),
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    plagued.messages = []
    plagued.affected_by = int(AffectFlag.PLAGUE | AffectFlag.INVISIBLE)
    plagued.affected = [
        AffectData(
            type="plague",
            level=1,
            duration=10,
            location=0,
            modifier=-5,
            bitvector=int(AffectFlag.PLAGUE),
        )
    ]
    room.people.append(plagued)
    character_registry.append(plagued)
    return plagued


def _make_pc_witness(room: Room) -> Character:
    witness = Character(
        name="Blindspot",
        is_npc=False,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    witness.messages = []
    room.people.append(witness)
    character_registry.append(witness)
    return witness


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
    proto = MobIndex(vnum=9581, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="someone writhes",
            code='mob echo "PLAGUE_SEEN"\n',
            vnum=9581,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def test_plague_tick_room_act_masks_name_and_fires_act_trigger() -> None:
    """ROM src/update.c:803 act(TO_ROOM) uses PERS and dispatches TRIG_ACT."""
    import mud.mobprog as mobprog
    from mud.game_loop import _char_update_tick_effects

    room = _make_room()
    plagued = _make_plagued(room)
    witness = _make_pc_witness(room)
    _make_listener(room)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        extracted = _char_update_tick_effects(plagued)
    finally:
        mobprog.mp_act_trigger = original

    assert extracted is False
    assert any("You writhe in agony from the plague." in message for message in plagued.messages)
    assert not any("Wraith writhes" in message for message in plagued.messages)
    assert any("Someone writhes in agony as plague sores erupt from his skin." in msg for msg in witness.messages)
    assert fired == [("watcher", "Someone writhes in agony as plague sores erupt from his skin.")]
