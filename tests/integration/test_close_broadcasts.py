"""BCAST-003 — ``do_close`` must emit all three ROM TO_ROOM broadcasts.

ROM contract (``src/act_move.c:457-552``):

- Portal branch (line 491-492) emits ``$n closes $p.`` TO_ROOM.
- Container branch (line 514-515) emits ``$n closes $p.`` TO_ROOM.
- Door branch:
    - line 534: ``$n closes the $d.`` TO_ROOM (actor's room, $d = exit keyword).
    - lines 545-547: loop in the linked room — ``The $d closes.`` to each
      person there ($d = reverse-exit keyword).

Audit row: ``docs/parity/audits/BROADCAST_COVERAGE.md`` row 3 — R=3 non-TO_CHAR
acts vs Py=0. Pre-fix the Python ``do_close`` returned only the actor's
"Ok." / "You close $p." string with no ``broadcast_room`` calls.
"""

from __future__ import annotations

import pytest

from mud.commands.doors import do_close
from mud.models.character import Character, PCData
from mud.models.constants import EX_ISDOOR, ContainerFlag, ItemType
from mud.models.room import Exit, Room
from mud.registry import room_registry


@pytest.fixture
def two_rooms_with_open_door():
    room1 = Room(vnum=99721, name="Close Probe A")
    room2 = Room(vnum=99722, name="Close Probe B")
    for r in (room1, room2):
        r.people = []
        r.contents = []
        r.exits = [None] * 6
    room_registry[99721] = room1
    room_registry[99722] = room2

    # Door east from room1 -> room2; reverse west from room2 -> room1.
    # Both sides start OPEN (no EX_CLOSED bit set).
    exit_e = Exit(vnum=99722, exit_info=EX_ISDOOR, keyword="door")
    exit_w = Exit(vnum=99721, exit_info=EX_ISDOOR, keyword="door")
    exit_e.to_room = room2
    exit_w.to_room = room1
    room1.exits[1] = exit_e  # Direction.EAST = 1
    room2.exits[3] = exit_w  # Direction.WEST = 3

    actor = Character(name="Closer", level=10, room=room1, is_npc=False, position=5)
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

    room_registry.pop(99721, None)
    room_registry.pop(99722, None)


def test_close_door_broadcasts_to_actor_room(two_rooms_with_open_door):
    """ROM src/act_move.c:534 — act("$n closes the $d.", ch, NULL, pexit->keyword, TO_ROOM)."""
    actor, witness_here, _wo, _r1, _r2 = two_rooms_with_open_door

    result = do_close(actor, "east")

    assert result == "Ok."
    assert "Closer closes the door." in witness_here.messages, (
        f"Witness in actor's room should see '$n closes the $d.'; got {witness_here.messages!r}"
    )
    assert "Closer closes the door." not in actor.messages, (
        "Actor must be excluded from the TO_ROOM broadcast"
    )


def test_close_door_notifies_linked_room(two_rooms_with_open_door):
    """ROM src/act_move.c:545-547 — loop ``The $d closes.`` to every person in to_room."""
    actor, _here, witness_other, _r1, _r2 = two_rooms_with_open_door

    do_close(actor, "east")

    assert "The door closes." in witness_other.messages, (
        f"Person in linked room should see 'The $d closes.'; got {witness_other.messages!r}"
    )


def test_close_portal_broadcasts_to_room(two_rooms_with_open_door, place_object_factory):
    """ROM src/act_move.c:491-492 — act("$n closes $p.", ch, obj, NULL, TO_ROOM)."""
    actor, witness_here, _wo, _r1, _r2 = two_rooms_with_open_door

    portal = place_object_factory(
        room_vnum=99721,
        proto_kwargs={
            "vnum": 99730,
            "name": "shimmering portal",
            "short_descr": "a shimmering portal",
            "item_type": int(ItemType.PORTAL),
        },
    )
    # Portal must be EX_ISDOOR and currently open (no EX_CLOSED bit).
    portal.value = [1, EX_ISDOOR, 0, 99722]

    do_close(actor, "portal")

    assert "Closer closes a shimmering portal." in witness_here.messages, (
        f"Witness should see '$n closes $p.'; got {witness_here.messages!r}"
    )


def test_close_container_broadcasts_to_room(two_rooms_with_open_door, place_object_factory):
    """ROM src/act_move.c:514-515 — act("$n closes $p.", ch, obj, NULL, TO_ROOM)."""
    actor, witness_here, _wo, _r1, _r2 = two_rooms_with_open_door

    chest = place_object_factory(
        room_vnum=99721,
        proto_kwargs={
            "vnum": 99731,
            "name": "wooden chest",
            "short_descr": "a wooden chest",
            "item_type": int(ItemType.CONTAINER),
        },
    )
    # Closeable, currently OPEN (no CLOSED bit).
    chest.value = [0, int(ContainerFlag.CLOSEABLE), 0, 0, 0]

    do_close(actor, "chest")

    assert "Closer closes a wooden chest." in witness_here.messages, (
        f"Witness should see '$n closes $p.'; got {witness_here.messages!r}"
    )
