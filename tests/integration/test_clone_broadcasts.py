"""BCAST-002 — do_clone TO_ROOM broadcasts on both branches.

ROM C: src/act_wiz.c:2406 ``act("$n has created $p.", ch, clone, NULL, TO_ROOM)``
       src/act_wiz.c:2450 ``act("$n has created $N.", ch, NULL, clone, TO_ROOM)``
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import mob_registry, obj_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob
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


def _imm(name: str, room_vnum: int, *, trust: int = 60):
    char = create_test_character(name, room_vnum)
    char.level = trust
    char.trust = trust
    return char


def _witness(name: str, room_vnum: int):
    char = create_test_character(name, room_vnum)
    char.level = 1
    char.messages = []
    return char


def test_clone_object_emits_to_room_broadcast() -> None:
    # mirrors ROM src/act_wiz.c:2406 — act("$n has created $p.", ch, clone, NULL, TO_ROOM)
    from mud.commands.imm_search import do_clone

    room = _room(40550)
    admin = _imm("Admin", 40550)
    bystander = _witness("Watcher", 40550)
    proto = ObjIndex(vnum=88560, name="amulet", short_descr="a silver amulet")
    obj_registry[88560] = proto
    original = Object(instance_id=None, prototype=proto)
    original.in_room = room
    if not hasattr(room, "contents") or room.contents is None:
        room.contents = []
    room.contents.append(original)
    try:
        result = do_clone(admin, "amulet")
        assert "clone" in result.lower()
        msgs = "\n".join(bystander.messages)
        assert "Admin has created a silver amulet" in msgs, (
            f"missing TO_ROOM broadcast; got: {bystander.messages!r}"
        )
        actor_msgs = "\n".join(getattr(admin, "messages", []))
        assert "Admin has created a silver amulet" not in actor_msgs
    finally:
        obj_registry.pop(88560, None)


# NOTE: Mob-branch test (`act("$n has created $N.", ch, NULL, clone, TO_ROOM)`
# at ROM src/act_wiz.c:2450) deferred — blocked by CLONE-001 (do_clone mob
# branch imports non-existent LEVEL_AVATAR / LEVEL_DEMI / LEVEL_GOD constants
# from mud.models.constants; the trust gate ImportErrors before reaching the
# broadcast point). See BROADCAST_COVERAGE.md Blocked rows for fix shape.
