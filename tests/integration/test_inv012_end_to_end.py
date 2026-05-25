"""INV-012 end-to-end production paths.

The INV-012 smoke tests in test_inv012_object_list_canonical.py exercise
each newly-live primitive at the unit level (spawn_object appends to the
registry; get_obj_world finds spawned objects; obj_update decrements
timers). This file bridges those primitives to the production gameplay
surface: an immortal-command path that walks the world-scoped registry
to find an object in a remote room.

ROM ref: src/handler.c get_obj_world (walks the global object_list, not
the current room) + src/act_wiz.c:1240-1279 do_ostat.

Before INV-012, the registry was never populated by spawn_object, so
get_obj_world returned None for every search and immortals could not
locate objects outside their current room without manually loading them.
"""

from __future__ import annotations

from mud.commands.imm_search import do_ostat
from mud.models.character import Character, character_registry
from mud.models.constants import LEVEL_IMMORTAL
from mud.models.obj import ObjIndex, object_registry
from mud.models.room import Room
from mud.registry import obj_registry, room_registry
from mud.spawning.obj_spawner import spawn_object


def _mk_room(vnum: int, name: str) -> Room:
    room = Room(vnum=vnum, name=name, description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _mk_immortal(name: str, room: Room) -> Character:
    imm = Character(name=name, level=LEVEL_IMMORTAL, is_npc=False)
    imm.trust = LEVEL_IMMORTAL
    room.add_character(imm)
    character_registry.append(imm)
    return imm


def test_ostat_finds_object_spawned_in_a_remote_room():
    """End-to-end: spawn_object populates the registry; do_ostat in
    room A finds an object spawned and placed in room B. Exercises the
    full production path through get_obj_world, which iterates the
    object_registry that INV-012 first wired up.
    """
    here = _mk_room(94001, "Throne Room")
    elsewhere = _mk_room(94002, "Distant Vault")

    proto = ObjIndex(
        vnum=94101,
        name="distantcrown findme",
        short_descr="a distant crown",
        description="A distant crown rests here.",
        item_type=9,  # ITEM_TREASURE
        level=20,
        weight=10,
        cost=500,
        condition=100,  # numeric (overrides ObjIndex's "P" flag default)
    )
    obj_registry[94101] = proto

    imm = _mk_immortal("Watcher", here)
    obj = spawn_object(94101)
    assert obj is not None, "spawn_object returned None"
    # Place the spawned object in the remote room.
    elsewhere.contents.append(obj)
    obj.in_room = elsewhere

    try:
        # Pre-conditions: spawn populated the global registry (INV-012/2);
        # ostat will use get_obj_world to walk it.
        assert obj in object_registry

        result = do_ostat(imm, "findme")

        assert "distant crown" in result.lower(), result
        assert f"Vnum: {proto.vnum}" in result, result
        # Sanity-check that the remote-room location is reflected in the
        # response or at least that ostat didn't silently return a
        # "no such object" message.
        assert "not exist" not in result.lower(), result
    finally:
        obj_registry.pop(94101, None)
        room_registry.pop(94001, None)
        room_registry.pop(94002, None)
