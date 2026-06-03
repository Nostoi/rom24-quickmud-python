"""BCAST-014 / BCAST-015 — do_mload and do_oload TO_ROOM broadcasts.

ROM C:
- do_mload — src/act_wiz.c:2512 ``act("$n has created $N!", ch, NULL, victim, TO_ROOM)``
- do_oload — src/act_wiz.c:2566 ``act("$n has created $p!", ch, obj, NULL, TO_ROOM)``
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.room import Room
from mud.registry import mob_registry, obj_registry, room_registry
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


def test_mload_emits_to_room_broadcast_with_victim_short_descr() -> None:
    # mirrors ROM src/act_wiz.c:2512 — act("$n has created $N!", ch, NULL, victim, TO_ROOM)
    from mud.commands.imm_load import do_mload

    room = _room(40150)
    admin = _imm("Admin", 40150)
    bystander = _witness("Watcher", 40150)
    proto = MobIndex(vnum=88160, short_descr="a small rat", level=1)
    mob_registry[88160] = proto
    try:
        result = do_mload(admin, "88160")
        assert "Ok" in result
        msgs = "\n".join(bystander.messages)
        assert "Admin has created a small rat" in msgs, f"missing TO_ROOM broadcast; got: {bystander.messages!r}"
        # actor must not see the room broadcast (ROM TO_ROOM excludes ch)
        actor_msgs = "\n".join(getattr(admin, "messages", []))
        assert "Admin has created a small rat" not in actor_msgs
    finally:
        mob_registry.pop(88160, None)


def test_oload_emits_to_room_broadcast_with_obj_short_descr() -> None:
    # mirrors ROM src/act_wiz.c:2566 — act("$n has created $p!", ch, obj, NULL, TO_ROOM)
    from mud.commands.imm_load import do_oload

    room = _room(40250)
    admin = _imm("Admin", 40250)
    bystander = _witness("Watcher", 40250)
    proto = ObjIndex(vnum=88260, name="widget", short_descr="a shiny widget")
    obj_registry[88260] = proto
    try:
        result = do_oload(admin, "88260")
        assert "Ok" in result
        msgs = "\n".join(bystander.messages)
        assert "Admin has created a shiny widget" in msgs, f"missing TO_ROOM broadcast; got: {bystander.messages!r}"
        actor_msgs = "\n".join(getattr(admin, "messages", []))
        assert "Admin has created a shiny widget" not in actor_msgs
    finally:
        obj_registry.pop(88260, None)
