"""BCAST-016 — ``do_open`` must emit all three ROM TO_ROOM broadcasts.

ROM contract (``src/act_move.c:345-453``):

- Portal branch (lines 382-385) emits ``$n opens $p.`` TO_ROOM.
- Container branch (lines 410-413) emits ``$n opens $p.`` TO_ROOM.
- Door branch:
    - line 436: ``$n opens the $d.`` TO_ROOM (actor's room, $d = exit keyword).
    - lines 447-448: loop in the linked room — ``The $d opens.`` to each
      person there ($d = reverse-exit keyword).

Audit row: ``docs/parity/audits/BROADCAST_COVERAGE.md`` row 16 — R=3 non-TO_CHAR
acts vs Py=0. Pre-fix the Python ``do_open`` returned only the actor's
"Ok." / "You open $p." string with no ``broadcast_room`` calls.
"""

from __future__ import annotations

import pytest

from mud.commands.doors import do_open
from mud.models.character import Character, PCData
from mud.models.constants import EX_CLOSED, EX_ISDOOR, ContainerFlag, ItemType
from mud.models.room import Exit, Room
from mud.registry import room_registry


@pytest.fixture
def two_rooms_with_door():
    room1 = Room(vnum=99701, name="Open Probe A")
    room2 = Room(vnum=99702, name="Open Probe B")
    for r in (room1, room2):
        r.people = []
        r.contents = []
        r.exits = [None] * 6
    room_registry[99701] = room1
    room_registry[99702] = room2

    # door east from room1 -> room2; reverse west from room2 -> room1
    exit_e = Exit(vnum=99702, exit_info=EX_ISDOOR | EX_CLOSED, keyword="door")
    exit_w = Exit(vnum=99701, exit_info=EX_ISDOOR | EX_CLOSED, keyword="door")
    exit_e.to_room = room2
    exit_w.to_room = room1
    room1.exits[1] = exit_e  # Direction.EAST = 1
    room2.exits[3] = exit_w  # Direction.WEST = 3

    actor = Character(name="Opener", level=10, room=room1, is_npc=False, position=5)
    actor.pcdata = PCData()
    actor.messages = []
    room1.people.append(actor)

    witness_here = Character(name="HereWatcher", level=10, room=room1, is_npc=False, position=5)
    witness_here.pcdata = PCData()
    witness_here.messages = []
    room1.people.append(witness_here)

    witness_other = Character(name="OtherWatcher", level=10, room=room2, is_npc=False, position=5)
    witness_other.pcdata = PCData()
    witness_other.messages = []
    room2.people.append(witness_other)

    yield actor, witness_here, witness_other, room1, room2

    room_registry.pop(99701, None)
    room_registry.pop(99702, None)


def test_open_door_broadcasts_to_actor_room(two_rooms_with_door):
    """ROM src/act_move.c:436 — act("$n opens the $d.", ch, NULL, pexit->keyword, TO_ROOM)."""
    actor, witness_here, _witness_other, _r1, _r2 = two_rooms_with_door

    result = do_open(actor, "east")

    assert result == "Ok."
    assert "Opener opens the door." in witness_here.messages, (
        f"Witness in actor's room should see '$n opens the $d.'; got {witness_here.messages!r}"
    )
    assert "Opener opens the door." not in actor.messages, (
        "Actor must be excluded from the TO_ROOM broadcast (ROM uses TO_ROOM, not TO_NOTVICT-style)"
    )


def test_open_door_notifies_linked_room(two_rooms_with_door):
    """ROM src/act_move.c:447-448 — loop ``The $d opens.`` to every person in to_room."""
    _actor, _witness_here, witness_other, _r1, _r2 = two_rooms_with_door

    do_open(_actor, "east")

    assert "The door opens." in witness_other.messages, (
        f"Person in linked room should see 'The $d opens.'; got {witness_other.messages!r}"
    )


def test_open_portal_broadcasts_to_room(two_rooms_with_door, place_object_factory):
    """ROM src/act_move.c:384 — act("$n opens $p.", ch, obj, NULL, TO_ROOM)."""
    actor, witness_here, _wo, _r1, _r2 = two_rooms_with_door

    portal = place_object_factory(
        room_vnum=99701,
        proto_kwargs={
            "vnum": 99710,
            "name": "shimmering portal",
            "short_descr": "a shimmering portal",
            "item_type": int(ItemType.PORTAL),
        },
    )
    # ROM portal needs EX_ISDOOR | EX_CLOSED to be openable
    portal.value = [1, EX_ISDOOR | EX_CLOSED, 0, 99702]

    do_open(actor, "portal")

    assert "Opener opens a shimmering portal." in witness_here.messages, (
        f"Witness should see '$n opens $p.'; got {witness_here.messages!r}"
    )


def test_open_container_broadcasts_to_room(two_rooms_with_door, place_object_factory):
    """ROM src/act_move.c:411-412 — act("$n opens $p.", ch, obj, NULL, TO_ROOM)."""
    actor, witness_here, _wo, _r1, _r2 = two_rooms_with_door

    chest = place_object_factory(
        room_vnum=99701,
        proto_kwargs={
            "vnum": 99711,
            "name": "wooden chest",
            "short_descr": "a wooden chest",
            "item_type": int(ItemType.CONTAINER),
        },
    )
    # closeable + currently closed; not locked
    chest.value = [0, int(ContainerFlag.CLOSEABLE | ContainerFlag.CLOSED), 0, 0, 0]

    do_open(actor, "chest")

    assert "Opener opens a wooden chest." in witness_here.messages, (
        f"Witness should see '$n opens $p.'; got {witness_here.messages!r}"
    )
