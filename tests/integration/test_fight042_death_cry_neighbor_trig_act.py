"""FIGHT-042 — death_cry's neighbor-room cry must dispatch TRIG_ACT to NPCs.

ROM ``death_cry`` (``src/fight.c:1677-1688``) loops over every exit and, with
``ch->in_room`` temporarily relocated to the adjacent room, emits
``act(msg, ch, NULL, NULL, TO_ROOM)`` (``:1685``) for each — with **no**
``MOBtrigger = FALSE`` wrap anywhere in ``death_cry``. Per ``src/comm.c:2384``
that means every NPC recipient in an adjacent room with ``HAS_TRIGGER(TRIG_ACT)``
matching the cry must receive ``mp_act_trigger``.

The Python ``_broadcast_neighbor_cry`` (``mud/combat/death.py``) delivered the
cry via ``target.broadcast(message)`` — visible-text delivery only, no actor,
no TRIG_ACT dispatch (INV-025 class, sibling of the in-room FIGHT-041 line).
This test pins the TRIG_ACT contract for the neighbor cry.
"""

from __future__ import annotations

import pytest

import mud.mobprog as mobprog
from mud.combat.death import death_cry
from mud.mobprog import Trigger
from mud.models.character import Character, character_registry
from mud.models.constants import Position, Sector
from mud.models.mob import MobIndex
from mud.models.room import Exit, Room
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name="Crypt", sector_type=int(Sector.CITY))
    room.people = []
    room.contents = []
    room.exits = [None] * 6
    return room


def _listener(room: Room, phrase: str, vnum: int) -> Character:
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
        _FakeProg(trig_type=int(Trigger.ACT), trig_phrase=phrase, code='mob echo "HEARD"\n', vnum=vnum)
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def test_neighbor_death_cry_fires_act_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rng_mm, "number_bits", lambda bits: 0)
    room = _room(9410)
    neighbor = _room(9411)
    exit_north = Exit(vnum=neighbor.vnum, exit_info=0, keyword="")
    exit_north.to_room = neighbor
    room.exits[0] = exit_north

    victim = Character(name="Victim", level=5, is_npc=False, room=room)
    room.people.append(victim)
    character_registry.append(victim)
    _listener(neighbor, "death", vnum=9412)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)

    death_cry(victim)

    # ROM src/fight.c:1685 — act(msg, ch, NULL, NULL, TO_ROOM) per exit, no
    # MOBtrigger wrap → NPC in the adjacent room receives mp_act_trigger.
    assert fired, "neighbor-room death cry must dispatch mp_act_trigger (ROM fight.c:1685, no MOBtrigger wrap)"
    assert any("death cry" in msg for _, msg in fired), fired
