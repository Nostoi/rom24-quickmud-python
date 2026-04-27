"""Integration tests for mob_prog.c cmd_eval predicates (MOB_PROG_C_AUDIT.md gaps).

Covers world-scoped predicates and other ``_cmd_eval`` divergences from
ROM ``src/mob_prog.c``.
"""

from __future__ import annotations

import pytest

from mud import mobprog
from mud.models.character import Character, character_registry
from mud.models.obj import ObjIndex, object_registry
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import obj_registry, room_registry


@pytest.fixture(autouse=True)
def _clear_registries():
    room_registry.clear()
    obj_registry.clear()
    character_registry.clear()
    object_registry.clear()
    yield
    room_registry.clear()
    obj_registry.clear()
    character_registry.clear()
    object_registry.clear()


def _make_obj(vnum: int, name: str, short_descr: str) -> Object:
    proto = ObjIndex(vnum=vnum, name=name, short_descr=short_descr)
    obj_registry[vnum] = proto
    obj = Object(instance_id=None, prototype=proto)
    object_registry.append(obj)
    return obj


def test_objexists_finds_object_in_remote_room_by_name():
    """mirrors ROM src/mob_prog.c:399 — objexists must walk the world."""
    here = Room(vnum=4000, name="Mob Room")
    elsewhere = Room(vnum=4100, name="Vault")
    room_registry[4000] = here
    room_registry[4100] = elsewhere

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    artifact = _make_obj(9999, "rare artifact relic", "a rare artifact")
    elsewhere.contents.append(artifact)
    artifact.location = elsewhere

    assert mobprog._cmd_eval("objexists", "artifact", mob, None, None, None, None) is True


def test_objexists_finds_object_in_remote_room_by_vnum():
    """mirrors ROM src/mob_prog.c:399 — objexists vnum branch must walk the world."""
    here = Room(vnum=4000, name="Mob Room")
    elsewhere = Room(vnum=4100, name="Vault")
    room_registry[4000] = here
    room_registry[4100] = elsewhere

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    artifact = _make_obj(9999, "amulet glowing", "a glowing amulet")
    elsewhere.contents.append(artifact)
    artifact.location = elsewhere

    assert mobprog._cmd_eval("objexists", "9999", mob, None, None, None, None) is True


def test_objexists_returns_false_when_object_not_in_world():
    """No matching object anywhere in object_registry → False."""
    here = Room(vnum=4000, name="Mob Room")
    room_registry[4000] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    # Unrelated object so registry isn't empty.
    _make_obj(123, "stick", "a stick")

    assert mobprog._cmd_eval("objexists", "phoenix", mob, None, None, None, None) is False
    assert mobprog._cmd_eval("objexists", "9999", mob, None, None, None, None) is False


def test_vnum_compare_against_pc_uses_zero_lval():
    """mirrors ROM src/mob_prog.c:631-648 — for PCs, lval stays 0; comparison still runs."""
    here = Room(vnum=4000, name="Hall")
    room_registry[4000] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    pc = Character(name="hero", is_npc=False)
    here.add_character(pc)
    character_registry.append(pc)

    # PC → lval = 0 → "$n vnum == 0" is True, "!= 0" is False, "> 0" is False.
    assert mobprog._cmd_eval("vnum", "$n == 0", mob, pc, None, None, None) is True
    assert mobprog._cmd_eval("vnum", "$n != 0", mob, pc, None, None, None) is False
    assert mobprog._cmd_eval("vnum", "$n > 0", mob, pc, None, None, None) is False


def test_vnum_compare_against_npc_uses_proto_vnum():
    """mirrors ROM src/mob_prog.c:640-642 — NPC vnum comes from pIndexData."""
    from mud.models.mob import MobIndex

    here = Room(vnum=4001, name="Hall")
    room_registry[4001] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    other_npc = Character(name="goblin", is_npc=True)
    other_npc.prototype = MobIndex(vnum=3500, short_descr="a goblin")
    here.add_character(other_npc)
    character_registry.append(other_npc)

    assert mobprog._cmd_eval("vnum", "$n == 3500", mob, other_npc, None, None, None) is True
    assert mobprog._cmd_eval("vnum", "$n == 0", mob, other_npc, None, None, None) is False
