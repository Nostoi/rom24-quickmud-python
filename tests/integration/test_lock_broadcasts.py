"""BCAST-013 — ``do_lock`` must emit all three ROM TO_ROOM broadcasts.

ROM contract (``src/act_move.c:571-702``):

- Portal branch (line 621-622) emits ``$n locks $p.`` TO_ROOM.
- Container branch (line 654-655) emits ``$n locks $p.`` TO_ROOM.
- Door branch (line 690) emits ``$n locks the $d.`` TO_ROOM.
- ROM does NOT broadcast to the linked room — it only flips
  ``pexit_rev->exit_info`` silently (line 697). This test pins that
  asymmetry so do not "fix" it.

Audit row: ``docs/parity/audits/BROADCAST_COVERAGE.md`` row 13 — R=3
non-TO_CHAR acts vs Py=0.
"""

from __future__ import annotations

import pytest

from mud.commands.doors import do_lock
from mud.models.character import Character, PCData
from mud.models.constants import EX_CLOSED, EX_ISDOOR, ContainerFlag, ItemType
from mud.models.room import Exit, Room
from mud.registry import room_registry


@pytest.fixture
def two_rooms_with_closed_door(object_factory):
    room1 = Room(vnum=99741, name="Lock Probe A")
    room2 = Room(vnum=99742, name="Lock Probe B")
    for r in (room1, room2):
        r.people = []
        r.contents = []
        r.exits = [None] * 6
    room_registry[99741] = room1
    room_registry[99742] = room2

    # Door east -> west, both currently CLOSED (lock requires closed).
    exit_e = Exit(vnum=99742, exit_info=EX_ISDOOR | EX_CLOSED, keyword="door", key=99799)
    exit_w = Exit(vnum=99741, exit_info=EX_ISDOOR | EX_CLOSED, keyword="door", key=99799)
    exit_e.to_room = room2
    exit_w.to_room = room1
    room1.exits[1] = exit_e
    room2.exits[3] = exit_w

    actor = Character(name="Locker", level=10, room=room1, is_npc=False, position=5)
    actor.pcdata = PCData()
    actor.messages = []
    # Give the actor the key
    key = object_factory(
        {"vnum": 99799, "name": "iron key", "short_descr": "an iron key", "item_type": int(ItemType.KEY)}
    )
    actor.inventory = [key]
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

    room_registry.pop(99741, None)
    room_registry.pop(99742, None)


def test_lock_door_broadcasts_to_actor_room(two_rooms_with_closed_door):
    """ROM src/act_move.c:690 — act("$n locks the $d.", ch, NULL, pexit->keyword, TO_ROOM)."""
    actor, witness_here, witness_other, _r1, _r2 = two_rooms_with_closed_door

    result = do_lock(actor, "east")

    assert result == "*Click*"
    assert "Locker locks the door." in witness_here.messages, (
        f"Witness in actor's room should see '$n locks the $d.'; got {witness_here.messages!r}"
    )
    # ROM pinning: NO linked-room broadcast on lock (line 697 silently
    # SET_BITs pexit_rev->exit_info but emits no act()).
    assert "Locker locks the door." not in witness_other.messages
    assert not any("locks" in m.lower() for m in witness_other.messages), (
        f"ROM do_lock has no linked-room broadcast; got {witness_other.messages!r}"
    )


def test_lock_portal_broadcasts_to_room(two_rooms_with_closed_door, place_object_factory):
    """ROM src/act_move.c:622 — act("$n locks $p.", ch, obj, NULL, TO_ROOM)."""
    actor, witness_here, _wo, _r1, _r2 = two_rooms_with_closed_door

    portal = place_object_factory(
        room_vnum=99741,
        proto_kwargs={
            "vnum": 99750,
            "name": "shimmering portal",
            "short_descr": "a shimmering portal",
            "item_type": int(ItemType.PORTAL),
        },
    )
    # Portal: ISDOOR + CLOSED, key vnum 99799 (actor already has it).
    portal.value = [1, EX_ISDOOR | EX_CLOSED, 0, 99742, 99799]

    do_lock(actor, "portal")

    assert "Locker locks a shimmering portal." in witness_here.messages, (
        f"Witness should see '$n locks $p.'; got {witness_here.messages!r}"
    )


def test_lock_container_broadcasts_to_room(two_rooms_with_closed_door, place_object_factory):
    """ROM src/act_move.c:655 — act("$n locks $p.", ch, obj, NULL, TO_ROOM)."""
    actor, witness_here, _wo, _r1, _r2 = two_rooms_with_closed_door

    chest = place_object_factory(
        room_vnum=99741,
        proto_kwargs={
            "vnum": 99751,
            "name": "iron chest",
            "short_descr": "an iron chest",
            "item_type": int(ItemType.CONTAINER),
        },
    )
    # Closeable + CLOSED, container key vnum in value[2] = 99799.
    chest.value = [0, int(ContainerFlag.CLOSEABLE | ContainerFlag.CLOSED), 99799, 0, 0]

    do_lock(actor, "chest")

    assert "Locker locks an iron chest." in witness_here.messages, (
        f"Witness should see '$n locks $p.'; got {witness_here.messages!r}"
    )
