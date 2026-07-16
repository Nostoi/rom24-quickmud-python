"""HANDLER-009 — MobInstance.move_to_room must head-insert like ROM char_to_room.

ROM src/handler.c:1557-1559 (char_to_room):

    ch->next_in_room = pRoomIndex->people;
    pRoomIndex->people = ch;

Every arrival is prepended — room.people is newest-arrival-first. Python's
`Room.add_character`/`Room.add_mob` correctly `insert(0)`, but
`MobInstance.move_to_room` `append`ed, so any caller inherited tail
placement, corrupting every room-people walk order (look listings,
check_assist's outer loop, the INV-045 room-head seed). Currently test-only
reach (production paths use Room.add_mob / mob_cmds._move_to_room), but the
divergence is latent for any future caller. Fix routes through Room.add_mob.
"""

from __future__ import annotations

import pytest

from mud.registry import room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.world import initialize_world

_ROOM_A = 3001
_ROOM_B = 3005


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_handler009_move_to_room_head_inserts() -> None:
    """mirrors ROM src/handler.c:1557-1559 — the arriving mob becomes the
    room-people head (newest first), same as Room.add_mob."""
    room = room_registry[_ROOM_B]

    first = spawn_mob(3003)
    second = spawn_mob(3003)
    assert first is not None and second is not None

    first.move_to_room(room)
    second.move_to_room(room)

    assert room.people[0] is second, (
        "move_to_room must head-insert (ROM char_to_room prepends, "
        f"src/handler.c:1557-1559); head is {room.people[0]!r}"
    )
    assert room.people.index(first) > room.people.index(second)


def test_handler009_move_to_room_departs_old_room() -> None:
    """Moving between rooms removes from the old room's people and
    head-inserts into the new one."""
    room_a = room_registry[_ROOM_A]
    room_b = room_registry[_ROOM_B]

    mob = spawn_mob(3003)
    assert mob is not None
    mob.move_to_room(room_a)
    assert mob in room_a.people and room_a.people[0] is mob

    mob.move_to_room(room_b)
    assert mob not in room_a.people
    assert room_b.people[0] is mob
    assert mob.room is room_b
