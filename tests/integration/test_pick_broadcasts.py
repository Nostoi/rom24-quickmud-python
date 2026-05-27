"""BCAST-034 — do_pick TO_ROOM broadcasts (portal, container, door).

ROM C:
- portal/container: src/act_move.c:907 / :945 — ``act("$n picks the lock on $p.", ch, obj, NULL, TO_ROOM)``
- door:             src/act_move.c:981       — ``act("$n picks the $d.", ch, NULL, pexit->keyword, TO_ROOM)``
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.models.constants import EX_CLOSED, EX_ISDOOR, EX_LOCKED, ContainerFlag, ItemType
from mud.models.room import Exit, Room
from mud.registry import room_registry
from mud.utils import rng_mm
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clean_state():
    rooms = set(room_registry)
    char_ids = {id(c) for c in character_registry}
    yield
    for vnum in list(room_registry):
        if vnum not in rooms:
            room_registry.pop(vnum, None)
    character_registry[:] = [c for c in character_registry if id(c) in char_ids]
    for attr in ("players", "char_list", "descriptor_list"):
        if hasattr(global_registry, attr):
            delattr(global_registry, attr)


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="")
    room_registry[vnum] = room
    return room


def _picker(name: str, room_vnum: int):
    char = create_test_character(name, room_vnum)
    char.level = 20
    char.trust = 20
    char.skills = {"pick lock": 100}
    char.messages = []
    return char


def _witness(name: str, room_vnum: int):
    char = create_test_character(name, room_vnum)
    char.level = 1
    char.messages = []
    return char


def _seed_skill_pass():
    # rng_mm.number_percent must roll <= skill (100), so any seed works,
    # but we pin one to keep the test deterministic across CI runs.
    rng_mm.seed_mm(42)


def test_pick_container_emits_to_room_broadcast() -> None:
    # mirrors ROM src/act_move.c:945 — act("$n picks the lock on $p.", ch, obj, NULL, TO_ROOM)
    from mud.commands.doors import do_pick
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    _seed_skill_pass()
    room = _room(50100)
    picker = _picker("Thief", 50100)
    bystander = _witness("Watcher", 50100)
    proto = ObjIndex(vnum=88700, name="chest", short_descr="a wooden chest")
    chest = Object(instance_id=None, prototype=proto)
    chest.item_type = ItemType.CONTAINER
    chest.value = [0, int(ContainerFlag.CLOSED | ContainerFlag.LOCKED), 1, 0, 0]
    chest.in_room = room
    room.contents = [chest]

    result = do_pick(picker, "chest")
    assert "pick the lock" in result.lower()
    msgs = "\n".join(bystander.messages)
    assert "Thief picks the lock on a wooden chest" in msgs, (
        f"missing TO_ROOM broadcast; got: {bystander.messages!r}"
    )
    actor_msgs = "\n".join(picker.messages)
    assert "Thief picks the lock on a wooden chest" not in actor_msgs


def test_pick_door_emits_to_room_broadcast_with_keyword() -> None:
    # mirrors ROM src/act_move.c:981 — act("$n picks the $d.", ch, NULL, pexit->keyword, TO_ROOM)
    from mud.commands.doors import do_pick

    _seed_skill_pass()
    here = _room(50200)
    there = _room(50201)
    picker = _picker("Thief", 50200)
    bystander = _witness("Watcher", 50200)
    pexit = Exit(
        to_room=there,
        keyword="gate iron",
        exit_info=EX_ISDOOR | EX_CLOSED | EX_LOCKED,
        key=88800,
    )
    here.exits = [None, pexit, None, None, None, None]  # EAST

    result = do_pick(picker, "gate")
    assert result == "*Click*"
    msgs = "\n".join(bystander.messages)
    # ROM `$d` substitution uses first word of keyword.
    assert "Thief picks the gate." in msgs, (
        f"missing TO_ROOM broadcast; got: {bystander.messages!r}"
    )
    actor_msgs = "\n".join(picker.messages)
    assert "Thief picks the gate." not in actor_msgs
