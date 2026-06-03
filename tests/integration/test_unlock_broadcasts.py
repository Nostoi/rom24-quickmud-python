"""BCAST-027 — ``do_unlock`` must emit all three ROM TO_ROOM broadcasts.

ROM contract (``src/act_move.c:706-835``):

- Portal branch (line 756-757) emits ``$n unlocks $p.`` TO_ROOM.
- Container branch (line 789-790) emits ``$n unlocks $p.`` TO_ROOM.
- Door branch (line 825) emits ``$n unlocks the $d.`` TO_ROOM.
- ROM does NOT broadcast to the linked room — it only flips
  ``pexit_rev->exit_info`` silently (line 832). Symmetric to lock.

Audit row: ``docs/parity/audits/BROADCAST_COVERAGE.md`` row 27 — R=3
non-TO_CHAR acts vs Py=0.
"""

from __future__ import annotations

import pytest

from mud.commands.doors import do_unlock
from mud.models.character import Character, PCData
from mud.models.constants import EX_CLOSED, EX_ISDOOR, EX_LOCKED, ContainerFlag, ItemType
from mud.models.room import Exit, Room
from mud.registry import room_registry


@pytest.fixture
def two_rooms_with_locked_door(object_factory):
    room1 = Room(vnum=99761, name="Unlock Probe A")
    room2 = Room(vnum=99762, name="Unlock Probe B")
    for r in (room1, room2):
        r.people = []
        r.contents = []
        r.exits = [None] * 6
    room_registry[99761] = room1
    room_registry[99762] = room2

    # Both sides CLOSED + LOCKED — unlock requires both.
    flags = EX_ISDOOR | EX_CLOSED | EX_LOCKED
    exit_e = Exit(vnum=99762, exit_info=flags, keyword="door", key=99899)
    exit_w = Exit(vnum=99761, exit_info=flags, keyword="door", key=99899)
    exit_e.to_room = room2
    exit_w.to_room = room1
    room1.exits[1] = exit_e
    room2.exits[3] = exit_w

    actor = Character(name="Unlocker", level=10, room=room1, is_npc=False, position=5)
    actor.pcdata = PCData()
    actor.messages = []
    key = object_factory(
        {"vnum": 99899, "name": "brass key", "short_descr": "a brass key", "item_type": int(ItemType.KEY)}
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

    room_registry.pop(99761, None)
    room_registry.pop(99762, None)


def test_unlock_door_broadcasts_to_actor_room(two_rooms_with_locked_door):
    """ROM src/act_move.c:825 — act("$n unlocks the $d.", ch, NULL, pexit->keyword, TO_ROOM)."""
    actor, witness_here, witness_other, _r1, _r2 = two_rooms_with_locked_door

    result = do_unlock(actor, "east")

    assert result == "*Click*"
    assert "Unlocker unlocks the door." in witness_here.messages, (
        f"Witness in actor's room should see '$n unlocks the $d.'; got {witness_here.messages!r}"
    )
    # ROM pinning: NO linked-room broadcast on unlock (line 832).
    assert not any("unlocks" in m.lower() for m in witness_other.messages), (
        f"ROM do_unlock has no linked-room broadcast; got {witness_other.messages!r}"
    )


def test_unlock_portal_broadcasts_to_room(two_rooms_with_locked_door, place_object_factory):
    """ROM src/act_move.c:757 — act("$n unlocks $p.", ch, obj, NULL, TO_ROOM)."""
    actor, witness_here, _wo, _r1, _r2 = two_rooms_with_locked_door

    portal = place_object_factory(
        room_vnum=99761,
        proto_kwargs={
            "vnum": 99770,
            "name": "shimmering portal",
            "short_descr": "a shimmering portal",
            "item_type": int(ItemType.PORTAL),
        },
    )
    portal.value = [1, EX_ISDOOR | EX_CLOSED | EX_LOCKED, 0, 99762, 99899]

    do_unlock(actor, "portal")

    assert "Unlocker unlocks a shimmering portal." in witness_here.messages, (
        f"Witness should see '$n unlocks $p.'; got {witness_here.messages!r}"
    )


def test_unlock_container_broadcasts_to_room(two_rooms_with_locked_door, place_object_factory):
    """ROM src/act_move.c:790 — act("$n unlocks $p.", ch, obj, NULL, TO_ROOM)."""
    actor, witness_here, _wo, _r1, _r2 = two_rooms_with_locked_door

    chest = place_object_factory(
        room_vnum=99761,
        proto_kwargs={
            "vnum": 99771,
            "name": "brass chest",
            "short_descr": "a brass chest",
            "item_type": int(ItemType.CONTAINER),
        },
    )
    flags = ContainerFlag.CLOSEABLE | ContainerFlag.CLOSED | ContainerFlag.LOCKED
    chest.value = [0, int(flags), 99899, 0, 0]

    do_unlock(actor, "chest")

    assert "Unlocker unlocks a brass chest." in witness_here.messages, (
        f"Witness should see '$n unlocks $p.'; got {witness_here.messages!r}"
    )
