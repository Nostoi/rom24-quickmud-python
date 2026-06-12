"""BCAST-035 — do_purge TO_ROOM (room-purge) and TO_NOTVICT (PC/NPC) broadcasts.

ROM C:
- room-purge:    src/act_wiz.c:2605 — ``act("$n purges the room!", ch, NULL, NULL, TO_ROOM)``
- PC disintegrate: src/act_wiz.c:2633 — ``act("$n disintegrates $N.", ch, 0, victim, TO_NOTVICT)``
- NPC purge:     src/act_wiz.c:2645 — ``act("$n purges $N.", ch, NULL, victim, TO_NOTVICT)``
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag
from mud.models.room import Room
from mud.registry import room_registry
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
    if hasattr(global_registry, "descriptor_list"):
        delattr(global_registry, "descriptor_list")


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="")
    room_registry[vnum] = room
    return room


def _imm(name: str, room_vnum: int, *, trust: int = 60):
    char = create_test_character(name, room_vnum)
    char.level = trust
    char.trust = trust
    char.messages = []
    return char


def _witness(name: str, room_vnum: int):
    char = create_test_character(name, room_vnum)
    char.level = 1
    char.messages = []
    return char


def _npc(short_descr: str, room: Room):
    npc = Character(name="rat", is_npc=True, level=1, room=room, hit=100, max_hit=100)
    npc.short_descr = short_descr
    npc.act = int(ActFlag.IS_NPC)
    room.people.append(npc)
    character_registry.append(npc)
    return npc


def test_purge_room_emits_to_room_broadcast() -> None:
    # mirrors ROM src/act_wiz.c:2605 — act("$n purges the room!", ch, NULL, NULL, TO_ROOM)
    from mud.commands.imm_load import do_purge

    _room(50300)
    admin = _imm("Admin", 50300)
    bystander = _witness("Watcher", 50300)
    result = do_purge(admin, "")
    assert "Ok" in result
    msgs = "\n".join(bystander.messages)
    assert "Admin purges the room!" in msgs, f"missing TO_ROOM broadcast; got: {bystander.messages!r}"
    actor_msgs = "\n".join(admin.messages)
    assert "Admin purges the room!" not in actor_msgs


def test_purge_npc_emits_to_notvict_broadcast() -> None:
    # mirrors ROM src/act_wiz.c:2645 — act("$n purges $N.", ch, NULL, victim, TO_NOTVICT)
    from mud.commands.imm_load import do_purge

    room = _room(50400)
    admin = _imm("Admin", 50400)
    bystander = _witness("Watcher", 50400)
    _npc("a small rat", room)
    result = do_purge(admin, "rat")
    assert "Ok" in result
    msgs = "\n".join(bystander.messages)
    assert "Admin purges a small rat." in msgs, f"missing TO_NOTVICT broadcast; got: {bystander.messages!r}"
    actor_msgs = "\n".join(admin.messages)
    assert "Admin purges a small rat." not in actor_msgs
