"""LOOK-001 — room occupant list shows an NPC's long_descr, not its PERS/name.

ROM src/act_info.c show_char_to_char_0: for an NPC whose position == start_pos
and whose long_descr is non-empty, the room listing shows the long_descr
(e.g. "Hassan is here, waiting to dispense some justice."), NOT the PERS
short name. Surfaced by the differential testing harness (FINDING-001):
Python's mud/world/look.py rendered the PERS name ("Hassan") for every room
occupant, and MobInstance never carried long_descr from its prototype.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.spawning.templates import MobInstance
from mud.world.look import look

LONG = "Hassan is here, waiting to dispense some justice."


def _observer(room: Room) -> Character:
    obs = Character(name="Watcher", level=10, is_npc=False, position=Position.STANDING)
    obs.room = room
    room.people.append(obs)
    return obs


def test_look_001_mob_instance_carries_long_descr_from_prototype():
    # ROM src/db.c:2040 create_mobile: mob->long_descr = str_dup(pMobIndex->long_descr)
    proto = MobIndex(vnum=9100, player_name="hassan", short_descr="Hassan", long_descr=LONG + "\n", level=10)
    mob = MobInstance.from_prototype(proto)
    assert (mob.long_descr or "").strip() == LONG


def test_look_001_room_shows_npc_long_descr_at_start_pos():
    # ROM src/act_info.c show_char_to_char_0: NPC at start_pos shows long_descr.
    room = Room(vnum=9100, name="Test Room", description="A test room.")
    proto = MobIndex(vnum=9100, player_name="hassan", short_descr="Hassan", long_descr=LONG + "\n", level=10)
    mob = MobInstance.from_prototype(proto)
    mob.room = room
    room.people.append(mob)

    observer = _observer(room)
    out = look(observer)

    assert LONG in out, f"expected NPC long_descr in room look, got:\n{out}"
    # the bare PERS name must NOT be the occupant rendering
    assert "Hassan" not in [ln.strip() for ln in out.split("\n")]


DESC = "Hassan is a tall, imposing guard with a stern gaze."


def test_look_002_mob_instance_carries_description_from_prototype():
    # ROM src/db.c create_mobile: mob->description = str_dup(pMobIndex->description)
    proto = MobIndex(vnum=9101, player_name="hassan", short_descr="hassan", description=DESC + "\n", level=10)
    mob = MobInstance.from_prototype(proto)
    assert (getattr(mob, "description", None) or "").strip() == DESC


def test_look_002_look_at_mob_shows_description():
    # ROM src/act_info.c show_char_to_char_1: shows victim->description when non-empty.
    room = Room(vnum=9101, name="Test Room", description="A test room.")
    proto = MobIndex(vnum=9101, player_name="hassan", short_descr="hassan", description=DESC + "\n", level=10)
    mob = MobInstance.from_prototype(proto)
    mob.room = room
    room.people.append(mob)

    observer = _observer(room)
    out = look(observer, "hassan")

    assert DESC in out, f"expected mob description from look-at-mob, got:\n{out}"
    assert "nothing special" not in out
