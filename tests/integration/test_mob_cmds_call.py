"""Integration tests for ``do_mpcall`` (MOBprog ``call`` script command).

ROM C reference: ``src/mob_cmds.c:1217-1252`` — ROM signature is
``mob call <vnum> [victim|null] [object1|null] [object2|null]``. ROM resolves
``vch`` via ``get_char_room`` and the two object args via ``get_obj_here`` and
forwards all four to ``program_flow``. Python had only parsed ``vnum`` and a
single victim, dropping ``obj1``/``obj2`` entirely so called sub-programs
could never receive object context.

Closes MOBCMD-015 + MOBCMD-016.
"""

from __future__ import annotations

import pytest

from mud import mobprog
from mud.mob_cmds import do_mpcall
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


@pytest.fixture(autouse=True)
def _reset_registries():
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()
    yield
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()


def _setup_room() -> Room:
    area = Area(vnum=1, name="Call Test Area")
    area_registry[1] = area
    room = Room(vnum=9200, name="Call Test Room", area=area)
    room_registry[room.vnum] = room
    return room


def _make_obj(name: str, vnum: int) -> Object:
    proto = ObjIndex(
        vnum=vnum,
        name=name,
        short_descr=f"a {name}",
        description=f"A test {name}.",
        item_type=1,
        level=1,
        value=[0, 0, 0, 0, 0],
    )
    obj_registry[vnum] = proto
    obj = Object(instance_id=None, prototype=proto)
    obj.value = list(proto.value)
    return obj


class TestMpCallForwardsObjectArgs:
    """MOBCMD-015 + MOBCMD-016: ``do_mpcall`` must accept four script args
    (vnum, victim, obj1, obj2) and resolve obj1/obj2 via ``get_obj_here``,
    then forward all four to ``call_prog`` so sub-programs receive the
    object context. ROM ``src/mob_cmds.c:1241-1251``."""

    def test_obj1_and_obj2_are_resolved_and_passed_through(self, monkeypatch):
        room = _setup_room()
        mob = Character(name="Caller", is_npc=True)
        room.add_character(mob)
        character_registry.append(mob)

        sword = _make_obj("sword", vnum=9201)
        shield = _make_obj("shield", vnum=9202)
        room.contents.append(sword)
        room.contents.append(shield)

        captured: dict = {}

        def fake_call_prog(vnum, mob_, actor=None, arg1=None, arg2=None, *, context=None):  # noqa: ANN001
            captured["vnum"] = vnum
            captured["mob"] = mob_
            captured["actor"] = actor
            captured["arg1"] = arg1
            captured["arg2"] = arg2
            return []

        monkeypatch.setattr(mobprog, "call_prog", fake_call_prog)

        do_mpcall(mob, "5100 null sword shield")

        assert captured["vnum"] == 5100
        assert captured["mob"] is mob
        assert captured["actor"] is None  # "null" → no character match
        assert captured["arg1"] is sword, (
            "obj1 token 'sword' was not resolved through get_obj_here equivalent"
            " — ROM src/mob_cmds.c:1244-1246 requires obj1 lookup."
        )
        assert captured["arg2"] is shield, (
            "obj2 token 'shield' was not resolved — ROM"
            " src/mob_cmds.c:1247-1249 requires obj2 lookup."
        )

    def test_missing_obj_args_pass_none(self, monkeypatch):
        """When the script omits obj1/obj2, ``call_prog`` must still receive
        them as ``None`` (ROM initialises them to NULL on lines 1239-1240)."""
        room = _setup_room()
        mob = Character(name="Caller", is_npc=True)
        room.add_character(mob)
        character_registry.append(mob)

        captured: dict = {}

        def fake_call_prog(vnum, mob_, actor=None, arg1=None, arg2=None, *, context=None):  # noqa: ANN001
            captured["arg1"] = arg1
            captured["arg2"] = arg2
            return []

        monkeypatch.setattr(mobprog, "call_prog", fake_call_prog)

        do_mpcall(mob, "5100")

        assert captured["arg1"] is None
        assert captured["arg2"] is None
